"""Verified, crash-safe client for task-v1/luminesk-database."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from luminesk_cli.domain.catalog import (
    DATABASE_REPOSITORY,
    GIT_REVISION_RE,
    MAX_CATALOG_SIZE,
    CatalogEntry,
    CatalogSnapshot,
    parse_catalog_index,
)
from luminesk_cli.domain.errors import ResolutionError, SecurityError, ValidationError
from luminesk_cli.domain.manifest import (
    MANIFEST_NAME,
    HttpOptions,
    SourceSpec,
    load_manifest,
)
from luminesk_cli.domain.primitives import safe_relative_path, validate_digest
from luminesk_cli.domain.recipe import RecipeSnapshot
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.fetch import SecureFetcher
from luminesk_cli.infrastructure.recipe_snapshot import create_recipe_snapshot
from luminesk_cli.infrastructure.sources.common import (
    request_json_object,
    request_metadata,
)
from luminesk_cli.infrastructure.state import atomic_write, canonical_json_bytes
from luminesk_cli.infrastructure.template import read_template_tree

DATABASE_OWNER = "task-v1"
DATABASE_NAME = "luminesk-database"
API_ROOT = f"https://api.github.com/repos/{DATABASE_OWNER}/{DATABASE_NAME}"
RAW_ROOT = f"https://raw.githubusercontent.com/{DATABASE_OWNER}/{DATABASE_NAME}"
MAX_INDEX_DIGEST_SIZE = 256
MAX_ENTRY_FILES = 4_096
MAX_ENTRY_SIZE = 64 * 1024 * 1024
SNAPSHOT_METADATA_FILE = "snapshot.json"


class CatalogStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    @property
    def active_path(self) -> Path:
        return self.root / "active.json"

    def commit(self, snapshot: CatalogSnapshot, content: bytes) -> None:
        parsed = parse_catalog_index(content)
        if parsed != snapshot:
            raise ValidationError("catalog snapshot does not match its index content")
        directory = self.root / "snapshots" / snapshot.revision
        index = directory / "index-v1.json"
        metadata = directory / SNAPSHOT_METADATA_FILE
        directory.mkdir(parents=True, exist_ok=True)
        metadata_content = canonical_json_bytes(
            {
                "repository": snapshot.repository,
                "revision": snapshot.revision,
                "indexDigest": snapshot.index_digest,
            }
        )
        self._write_once(index, content)
        self._write_once(metadata, metadata_content)
        self._activate(snapshot)

    def load_active(self) -> CatalogSnapshot:
        if not self.active_path.is_file():
            raise ValidationError(
                "Catalog is unavailable. Run `nesk catalog update` first."
            )
        try:
            value = json.loads(self.active_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError("active catalog pointer is corrupt") from exc
        if not isinstance(value, dict) or set(value) != {
            "repository",
            "revision",
            "indexDigest",
        }:
            raise ValidationError("active catalog pointer is invalid")
        if value["repository"] != DATABASE_REPOSITORY:
            raise ValidationError("active catalog repository is not official")
        revision = value["revision"]
        if not isinstance(revision, str) or GIT_REVISION_RE.fullmatch(revision) is None:
            raise ValidationError("active catalog revision is invalid")
        digest = validate_digest(value["indexDigest"], "catalog.active.indexDigest")
        return self._load_revision(revision, expected_digest=digest)

    def verify(self) -> CatalogSnapshot:
        return self.load_active()

    def use(self, revision: str) -> CatalogSnapshot:
        if GIT_REVISION_RE.fullmatch(revision) is None:
            raise ValidationError("catalog revision must be a lowercase Git commit SHA")
        snapshot = self._load_revision(revision)
        self._activate(snapshot)
        return snapshot

    def _load_revision(
        self,
        revision: str,
        *,
        expected_digest: str | None = None,
    ) -> CatalogSnapshot:
        directory = self.root / "snapshots" / revision
        metadata_path = directory / SNAPSHOT_METADATA_FILE
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(
                f"catalog snapshot is not cached: {revision}"
            ) from exc
        if not isinstance(metadata, dict) or set(metadata) != {
            "repository",
            "revision",
            "indexDigest",
        }:
            raise SecurityError("cached catalog snapshot metadata is invalid")
        if metadata["repository"] != DATABASE_REPOSITORY:
            raise SecurityError("cached catalog snapshot repository is not official")
        if metadata["revision"] != revision:
            raise SecurityError(
                "cached catalog snapshot revision does not match its path"
            )
        digest = validate_digest(
            metadata["indexDigest"], "catalog.snapshot.indexDigest"
        )
        if expected_digest is not None and digest != expected_digest:
            raise SecurityError("active catalog digest does not match cached metadata")

        path = directory / "index-v1.json"
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ValidationError("active catalog index is missing") from exc
        if _digest(content) != digest:
            raise SecurityError("cached catalog index digest does not match metadata")
        snapshot = parse_catalog_index(content, source=str(path))
        if snapshot.revision != revision:
            raise SecurityError("cached catalog index revision does not match its path")
        return snapshot

    def _activate(self, snapshot: CatalogSnapshot) -> None:
        atomic_write(
            self.active_path,
            canonical_json_bytes(
                {
                    "repository": snapshot.repository,
                    "revision": snapshot.revision,
                    "indexDigest": snapshot.index_digest,
                }
            ),
        )

    @staticmethod
    def _write_once(path: Path, content: bytes) -> None:
        if path.exists():
            try:
                existing = path.read_bytes()
            except OSError as exc:
                raise ValidationError(
                    f"cannot read cached catalog file: {path}"
                ) from exc
            if existing != content:
                raise SecurityError(
                    "catalog snapshot collision for an immutable database commit",
                    path=str(path),
                )
            return
        atomic_write(path, content)


class CatalogClient:
    def __init__(
        self,
        store: CatalogStore,
        *,
        client: httpx.Client | None = None,
        allow_private_network: bool = False,
    ) -> None:
        self.store = store
        self.client = client
        self.allow_private_network = allow_private_network

    def update(self) -> CatalogSnapshot:
        owned_client = self.client is None
        client = self.client or httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
        )
        try:
            revision = self._resolve_revision(client)
            metadata_source = self._metadata_source()
            digest_response = request_metadata(
                client,
                f"{RAW_ROOT}/{revision}/dist/index-v1.json.sha256",
                metadata_source,
                headers=_github_headers(),
            )
            if len(digest_response.content) > MAX_INDEX_DIGEST_SIZE:
                raise SecurityError("catalog digest file exceeds size limit")
            expected_digest = _parse_digest_file(digest_response.content)
            fetcher = SecureFetcher(
                ContentCache(self.store.root / "blobs"),
                client=client,
            )
            blob = fetcher.fetch(
                f"{RAW_ROOT}/{revision}/dist/index-v1.json",
                max_size=MAX_CATALOG_SIZE,
                expected_digest=expected_digest,
                allow_private_network=self.allow_private_network,
            )
            content = blob.path.read_bytes()
            snapshot = parse_catalog_index(content)
            if snapshot.revision != revision:
                raise SecurityError(
                    "catalog index revision does not match the resolved database commit"
                )
            self.store.commit(snapshot, content)
            return snapshot
        finally:
            if owned_client:
                client.close()

    def acquire_entry(
        self,
        snapshot: CatalogSnapshot,
        entry: CatalogEntry,
        destination: Path,
    ) -> RecipeSnapshot:
        if entry not in snapshot.entries:
            raise ValidationError(
                "catalog entry does not belong to the active snapshot"
            )
        if destination.exists() and (
            not destination.is_dir() or any(destination.iterdir())
        ):
            raise ValidationError("catalog recipe target must be an empty directory")
        destination.mkdir(parents=True, exist_ok=True)
        owned_client = self.client is None
        client = self.client or httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
        )
        try:
            self._fetch_manifest(client, snapshot, entry, destination)
            manifest = load_manifest(destination / MANIFEST_NAME)
            _validate_entry_manifest(entry, manifest)
            paths = []
            if manifest.template is not None:
                paths.append(manifest.template)
            paths.extend(file.source for file in manifest.files)
            if manifest.build is not None:
                paths.append(manifest.build.file)
            budget = _EntryBudget()
            for relative in dict.fromkeys(paths):
                self._fetch_declared_path(
                    client,
                    snapshot,
                    entry,
                    relative,
                    destination,
                    budget,
                )

            tree = read_template_tree(destination, manifest)
            actual_template_digest = tree.digest if tree is not None else None
            if actual_template_digest != entry.template_digest:
                raise SecurityError(
                    "catalog entry template digest does not match index"
                )
            return create_recipe_snapshot(
                destination,
                manifest,
                kind="database",
                source=DATABASE_REPOSITORY,
                revision=snapshot.revision,
                tracking=True,
                entry=entry.name,
                path=entry.path,
            )
        except BaseException:
            shutil.rmtree(destination, ignore_errors=True)
            raise
        finally:
            if owned_client:
                client.close()

    def _resolve_revision(self, client: httpx.Client) -> str:
        source = self._metadata_source()
        repository = request_json_object(
            client,
            API_ROOT,
            source,
            headers=_github_headers(),
        )
        branch = repository.get("default_branch")
        if not isinstance(branch, str) or not branch:
            raise ResolutionError("luminesk-database has no default branch")
        commit = request_json_object(
            client,
            f"{API_ROOT}/commits/{quote(branch, safe='')}",
            source,
            headers=_github_headers(),
        )
        revision = commit.get("sha")
        if not isinstance(revision, str) or GIT_REVISION_RE.fullmatch(revision) is None:
            raise ResolutionError("luminesk-database commit metadata has no valid SHA")
        return revision

    def _fetch_manifest(
        self,
        client: httpx.Client,
        snapshot: CatalogSnapshot,
        entry: CatalogEntry,
        destination: Path,
    ) -> None:
        fetcher = SecureFetcher(ContentCache(self.store.root / "blobs"), client=client)
        blob = fetcher.fetch(
            f"{RAW_ROOT}/{snapshot.revision}/{entry.path}/{MANIFEST_NAME}",
            max_size=1024 * 1024,
            expected_digest=entry.manifest_digest,
            allow_private_network=self.allow_private_network,
        )
        atomic_write(destination / MANIFEST_NAME, blob.path.read_bytes())

    def _fetch_declared_path(
        self,
        client: httpx.Client,
        snapshot: CatalogSnapshot,
        entry: CatalogEntry,
        relative: str,
        destination: Path,
        budget: _EntryBudget,
    ) -> None:
        safe = safe_relative_path(relative, "catalog.recipe.asset")
        full = f"{entry.path}/{safe}"
        url = f"{API_ROOT}/contents/{quote(full, safe='/')}?ref={snapshot.revision}"
        response = request_metadata(
            client,
            url,
            self._metadata_source(),
            headers=_github_headers(),
        )
        try:
            value = response.json()
        except ValueError as exc:
            raise ResolutionError("GitHub contents metadata is not valid JSON") from exc
        self._materialize_content_value(
            client,
            snapshot,
            entry,
            value,
            destination,
            budget,
        )

    def _materialize_content_value(
        self,
        client: httpx.Client,
        snapshot: CatalogSnapshot,
        entry: CatalogEntry,
        value: Any,
        destination: Path,
        budget: _EntryBudget,
    ) -> None:
        items = value if isinstance(value, list) else [value]
        if not all(isinstance(item, dict) for item in items):
            raise ResolutionError("GitHub contents metadata has an invalid shape")

        for item in items:
            item_type = item.get("type")
            raw_path = item.get("path")
            if not isinstance(raw_path, str):
                raise ResolutionError("GitHub contents entry has no path")
            full_path = safe_relative_path(raw_path, "catalog.github.path")
            prefix = f"{entry.path}/"
            if not full_path.startswith(prefix):
                raise SecurityError("database asset escapes its root entry")
            relative = full_path.removeprefix(prefix)
            target = destination / relative

            if item_type == "dir":
                target.mkdir(parents=True, exist_ok=True)
                self._fetch_declared_path(
                    client,
                    snapshot,
                    entry,
                    relative,
                    destination,
                    budget,
                )
                continue
            if item_type != "file":
                raise SecurityError(
                    "database recipe symlinks and special entries are forbidden"
                )
            size = item.get("size")
            download_url = item.get("download_url")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise ResolutionError("GitHub contents file has an invalid size")
            if not isinstance(download_url, str):
                raise ResolutionError("GitHub contents file has no download URL")
            if not budget.add(relative, size):
                continue
            fetcher = SecureFetcher(
                ContentCache(self.store.root / "blobs"), client=client
            )
            blob = fetcher.fetch(
                download_url,
                max_size=min(MAX_ENTRY_SIZE, max(size, 1)),
                expected_size=size,
                allow_private_network=self.allow_private_network,
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(target, blob.path.read_bytes())

    def _metadata_source(self) -> SourceSpec:
        return SourceSpec(
            id="catalog",
            type="http",
            target="metadata.json",
            options=HttpOptions(url="https://api.github.com/"),
            allow_private_network=self.allow_private_network,
        )


class _EntryBudget:
    def __init__(self) -> None:
        self.files = 0
        self.size = 0
        self.paths: set[str] = set()

    def add(self, path: str, size: int) -> bool:
        if path in self.paths:
            return False
        self.paths.add(path)
        self.files += 1
        self.size += size
        if self.files > MAX_ENTRY_FILES:
            raise SecurityError("database recipe contains too many files")
        if self.size > MAX_ENTRY_SIZE:
            raise SecurityError("database recipe exceeds total size limit")
        return True


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nesk/2.0 (https://github.com/task-v1/luminesk-cli)",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_digest_file(content: bytes) -> str:
    try:
        text = content.decode("ascii").strip().split()[0]
    except (UnicodeDecodeError, IndexError) as exc:
        raise ValidationError("catalog digest file is invalid") from exc
    if text.startswith("sha256:"):
        return validate_digest(text, "catalog.digest")
    if re.fullmatch(r"[0-9a-f]{64}", text) is None:
        raise ValidationError("catalog digest file is invalid")
    return f"sha256:{text}"


def _validate_entry_manifest(entry: CatalogEntry, manifest: Any) -> None:
    package = manifest.package
    if package.name != entry.name:
        raise SecurityError("catalog entry name does not match manifest package")
    if package.version != entry.recipe_version:
        raise SecurityError("catalog recipe version does not match manifest")
    if (
        package.kind != entry.kind
        or package.game != entry.game
        or package.edition != entry.edition
    ):
        raise SecurityError("catalog metadata does not match manifest")


def _digest(content: bytes) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(content).hexdigest()}"
