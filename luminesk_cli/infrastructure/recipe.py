"""Bounded Git recipe checkout and empty-target materialization."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from luminesk_cli.domain.errors import (
    ConflictError,
    NetworkError,
    ResolutionError,
    SecurityError,
)
from luminesk_cli.domain.manifest import (
    MANIFEST_NAME,
    HttpOptions,
    SourceSpec,
    load_manifest,
)
from luminesk_cli.domain.primitives import safe_relative_path
from luminesk_cli.domain.recipe import RecipeSnapshot
from luminesk_cli.infrastructure.cache import ContentCache, digest_file
from luminesk_cli.infrastructure.fetch import SecureFetcher
from luminesk_cli.infrastructure.github_contents import GitHubContentsFetcher
from luminesk_cli.infrastructure.recipe_snapshot import (
    create_recipe_snapshot,
    declared_recipe_assets,
)
from luminesk_cli.infrastructure.security.archive import ArchiveLimits, extract_archive
from luminesk_cli.infrastructure.sources.common import request_json_object
from luminesk_cli.infrastructure.state import atomic_write

MAX_RECIPE_FILES = 20_000
MAX_RECIPE_SIZE = 128 * 1024 * 1024
GITHUB_PART_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
GIT_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")


@dataclass(slots=True, frozen=True)
class GitRecipeSource:
    canonical: str
    clone_url: str
    owner: str
    repository: str
    requested_ref: str | None


@dataclass(slots=True, frozen=True)
class RecipeCheckout:
    root: Path
    source: GitRecipeSource
    revision: str
    tracking_ref: str | None
    tracked_files: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class MaterializedFile:
    path: str
    digest: str


def normalize_git_source(
    value: str, explicit_ref: str | None = None
) -> GitRecipeSource:
    source = value.strip()
    requested_ref = explicit_ref

    if source.startswith("github:"):
        shorthand = source.removeprefix("github:")
    elif source.startswith("https://github.com/"):
        shorthand = source.removeprefix("https://github.com/")
    elif "://" in source:
        raise ResolutionError("only HTTPS GitHub recipe URLs are supported")
    else:
        shorthand = source

    if requested_ref is None and "@" in shorthand:
        shorthand, requested_ref = shorthand.rsplit("@", 1)
    shorthand = shorthand.removesuffix(".git")

    parts = shorthand.strip("/").split("/")

    if len(parts) != 2 or not all(GITHUB_PART_RE.fullmatch(part) for part in parts):
        raise ResolutionError("recipe source must be OWNER/REPO")

    if requested_ref is not None and not GIT_REF_RE.fullmatch(requested_ref):
        raise ResolutionError("Git ref contains unsupported characters")

    owner, repository = parts
    return GitRecipeSource(
        canonical=f"github:{owner}/{repository}",
        clone_url=f"https://github.com/{owner}/{repository}.git",
        owner=owner,
        repository=repository,
        requested_ref=requested_ref,
    )


def checkout_recipe(
    source: GitRecipeSource,
    destination: Path,
    *,
    require_git: bool = False,
) -> RecipeCheckout:
    if not require_git:
        return _checkout_github_archive(source, destination)

    if shutil.which("git") is None:
        raise ResolutionError(
            "--keep-git requires the git executable; install Git or omit --keep-git"
        )

    return _checkout_with_git(source, destination)


def acquire_github_recipe(
    source: GitRecipeSource,
    destination: Path,
    cache: ContentCache,
    *,
    client: httpx.Client | None = None,
    allow_private_network: bool = False,
) -> RecipeSnapshot:
    """Acquire a GitHub recipe at an exact commit without polluting an instance."""

    if destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise ConflictError("GitHub recipe target must be an empty directory")
    destination.mkdir(parents=True, exist_ok=True)
    owned_client = client is None
    active_client = client or httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=False,
    )
    metadata_source = SourceSpec(
        id="recipe",
        type="http",
        target="metadata.json",
        options=HttpOptions(url="https://api.github.com/"),
        allow_private_network=allow_private_network,
    )
    headers = _github_headers()
    api_root = f"https://api.github.com/repos/{source.owner}/{source.repository}"

    try:
        revision, tracking_ref = _resolve_github_revision(
            active_client,
            source,
            api_root,
            metadata_source,
            headers,
        )
        manifest_blob = SecureFetcher(cache, client=active_client).fetch(
            "https://raw.githubusercontent.com/"
            f"{source.owner}/{source.repository}/{revision}/{MANIFEST_NAME}",
            max_size=1024 * 1024,
            allow_private_network=allow_private_network,
            headers=headers,
        )
        atomic_write(destination / MANIFEST_NAME, manifest_blob.path.read_bytes())
        manifest = load_manifest(destination / MANIFEST_NAME)

        if manifest.build is not None:
            manifest_digest = manifest.digest
            _materialize_exact_archive(
                active_client,
                api_root,
                revision,
                destination,
                cache,
                headers,
                allow_private_network=allow_private_network,
            )
            manifest = load_manifest(destination / MANIFEST_NAME)
            if manifest.digest != manifest_digest:
                raise SecurityError(
                    "GitHub archive manifest differs from the manifest fetched first"
                )
        else:
            GitHubContentsFetcher(
                client=active_client,
                cache=cache,
                api_root=api_root,
                revision=revision,
                metadata_source=metadata_source,
                headers=headers,
                max_files=MAX_RECIPE_FILES,
                max_size=MAX_RECIPE_SIZE,
            ).fetch(declared_recipe_assets(manifest), destination)

        return create_recipe_snapshot(
            destination,
            manifest,
            kind="github",
            source=source.canonical,
            revision=revision,
            ref=tracking_ref or source.requested_ref,
            tracking=tracking_ref is not None,
        )
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        if owned_client:
            active_client.close()


def _resolve_github_revision(
    client: httpx.Client,
    source: GitRecipeSource,
    api_root: str,
    metadata_source: SourceSpec,
    headers: dict[str, str],
) -> tuple[str, str | None]:
    requested_ref = source.requested_ref
    tracking_ref = None
    if requested_ref is None:
        repository = request_json_object(
            client,
            api_root,
            metadata_source,
            headers=headers,
        )
        default_branch = repository.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            raise ResolutionError("GitHub repository has no default branch")
        requested_ref = default_branch
        tracking_ref = default_branch
    else:
        branch_url = f"{api_root}/branches/{quote(requested_ref, safe='')}"
        try:
            branch = request_json_object(
                client,
                branch_url,
                metadata_source,
                headers=headers,
            )
            if branch.get("name") == requested_ref:
                tracking_ref = requested_ref
        except NetworkError as exc:
            if exc.details.get("status") != 404:
                raise

    commit = request_json_object(
        client,
        f"{api_root}/commits/{quote(requested_ref, safe='')}",
        metadata_source,
        headers=headers,
    )
    revision = commit.get("sha")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise ResolutionError("GitHub commit metadata has no valid SHA")
    return revision.lower(), tracking_ref


def _materialize_exact_archive(
    client: httpx.Client,
    api_root: str,
    revision: str,
    destination: Path,
    cache: ContentCache,
    headers: dict[str, str],
    *,
    allow_private_network: bool,
) -> None:
    blob = SecureFetcher(cache, client=client).fetch(
        f"{api_root}/tarball/{revision}",
        max_size=MAX_RECIPE_SIZE,
        headers=headers,
        allow_private_network=allow_private_network,
    )
    with tempfile.TemporaryDirectory(
        prefix="nesk-recipe-build-", dir=destination.parent
    ) as extraction_name:
        extraction = Path(extraction_name)
        extract_archive(
            blob.path,
            extraction,
            limits=ArchiveLimits(
                max_files=MAX_RECIPE_FILES + 1,
                max_file_size=MAX_RECIPE_SIZE,
                max_total_size=MAX_RECIPE_SIZE,
                max_compression_ratio=200,
            ),
        )
        roots = list(extraction.iterdir())
        if len(roots) != 1 or not roots[0].is_dir():
            raise SecurityError("GitHub recipe archive has an invalid root layout")
        tracked_files = tuple(
            path.relative_to(roots[0]).as_posix()
            for path in roots[0].rglob("*")
            if path.is_file()
        )
        _validate_checkout(roots[0], tracked_files)
        shutil.rmtree(destination)
        destination.mkdir()
        for item in roots[0].iterdir():
            shutil.move(str(item), destination / item.name)


def _checkout_with_git(source: GitRecipeSource, destination: Path) -> RecipeCheckout:
    destination.mkdir(parents=True)
    _git(destination, "init", "--quiet")
    _git(destination, "remote", "add", "origin", source.clone_url)
    default_branch = None

    if source.requested_ref is None:
        remote_head = _git(destination, "ls-remote", "--symref", "origin", "HEAD")
        first_line = remote_head.splitlines()[0] if remote_head else ""

        if first_line.startswith("ref: refs/heads/"):
            default_branch = first_line.split("\t", 1)[0].removeprefix(
                "ref: refs/heads/"
            )

    fetch_ref = source.requested_ref or default_branch or "HEAD"
    _git(destination, "fetch", "--quiet", "--depth=1", "--no-tags", "origin", fetch_ref)
    _git(destination, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    revision = _git(destination, "rev-parse", "HEAD").strip()
    tracked_raw = _git(destination, "ls-files", "-z")
    tracked_files = tuple(item for item in tracked_raw.split("\x00") if item)
    _validate_checkout(destination, tracked_files)
    tracking_ref = default_branch or _tracking_ref(destination, source.requested_ref)
    return RecipeCheckout(
        root=destination,
        source=source,
        revision=revision,
        tracking_ref=tracking_ref,
        tracked_files=tracked_files,
    )


def _checkout_github_archive(
    source: GitRecipeSource,
    destination: Path,
) -> RecipeCheckout:
    metadata_source = SourceSpec(
        id="recipe",
        type="http",
        target="recipe.tar.gz",
        options=HttpOptions(url="https://api.github.com/"),
    )
    headers = _github_headers()

    api_root = f"https://api.github.com/repos/{source.owner}/{source.repository}"

    with httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=False,
    ) as client:
        requested_ref = source.requested_ref
        tracking_ref = None

        if requested_ref is None:
            repository = request_json_object(
                client, api_root, metadata_source, headers=headers
            )
            default_branch = repository.get("default_branch")

            if not isinstance(default_branch, str) or not default_branch:
                raise ResolutionError("GitHub repository has no default branch")

            requested_ref = default_branch
            tracking_ref = default_branch
        else:
            branch_url = f"{api_root}/branches/{quote(requested_ref, safe='')}"

            try:
                branch = request_json_object(
                    client,
                    branch_url,
                    metadata_source,
                    headers=headers,
                )
                branch_name = branch.get("name")

                if branch_name == requested_ref:
                    tracking_ref = requested_ref
            except NetworkError as exc:
                if exc.details.get("status") != 404:
                    raise

                tracking_ref = None

        commit = request_json_object(
            client,
            f"{api_root}/commits/{quote(requested_ref, safe='')}",
            metadata_source,
            headers=headers,
        )
        revision = commit.get("sha")

        if not isinstance(revision, str) or not re.fullmatch(
            r"[0-9a-fA-F]{40}", revision
        ):
            raise ResolutionError("GitHub commit metadata has no valid SHA")

        archive_url = f"{api_root}/tarball/{revision}"
        archive_cache = ContentCache(destination.parent / ".recipe-cache")
        blob = SecureFetcher(archive_cache, client=client).fetch(
            archive_url,
            max_size=MAX_RECIPE_SIZE,
            headers=headers,
        )

    with tempfile.TemporaryDirectory(
        prefix="nesk-recipe-extract-", dir=destination.parent
    ) as extraction_name:
        extraction = Path(extraction_name)
        extract_archive(
            blob.path,
            extraction,
            limits=ArchiveLimits(
                max_files=MAX_RECIPE_FILES + 1,
                max_file_size=MAX_RECIPE_SIZE,
                max_total_size=MAX_RECIPE_SIZE,
                max_compression_ratio=200,
            ),
        )
        roots = list(extraction.iterdir())

        if len(roots) != 1 or not roots[0].is_dir():
            raise SecurityError("GitHub recipe archive has an invalid root layout")

        destination.mkdir(parents=True)

        for item in roots[0].iterdir():
            shutil.move(str(item), destination / item.name)

    tracked_files = tuple(
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    )
    _validate_checkout(destination, tracked_files)
    shutil.rmtree(destination.parent / ".recipe-cache", ignore_errors=True)
    return RecipeCheckout(
        root=destination,
        source=source,
        revision=revision.lower(),
        tracking_ref=tracking_ref,
        tracked_files=tracked_files,
    )


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nesk/2",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")

    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def ensure_empty_target(target: Path) -> None:
    if target.exists():
        if not target.is_dir() or any(target.iterdir()):
            raise ConflictError(
                "remote recipe target must be an empty directory",
                target=str(target.resolve()),
            )


def materialize_checkout(
    checkout: RecipeCheckout,
    target: Path,
    *,
    keep_git: bool = False,
) -> tuple[MaterializedFile, ...]:
    ensure_empty_target(target)
    target.mkdir(parents=True, exist_ok=True)
    copied: list[MaterializedFile] = []

    try:
        for relative in checkout.tracked_files:
            safe_relative_path(relative, "recipe.checkout.path")
            source = checkout.root / relative
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            digest, _ = digest_file(destination)
            copied.append(MaterializedFile(relative, digest))

        if keep_git:
            git_source = checkout.root / ".git"

            if not git_source.is_dir():
                raise SecurityError("Git checkout metadata is missing")

            _copy_tree_files(
                git_source,
                target / ".git",
                copied,
                prefix=".git",
                max_size=MAX_RECIPE_SIZE,
                max_files=MAX_RECIPE_FILES,
            )
    except BaseException:
        cleanup_materialized(target, tuple(copied))
        raise

    return tuple(copied)


def materialize_local_recipe(
    source: Path, target: Path
) -> tuple[MaterializedFile, ...]:
    """Copy a bounded local recipe tree into an empty target."""

    ensure_empty_target(target)
    target.mkdir(parents=True, exist_ok=True)
    copied: list[MaterializedFile] = []

    try:
        _copy_tree_files(
            source,
            target,
            copied,
            excluded={".git", ".luminesk_cli"},
            max_size=MAX_RECIPE_SIZE,
            max_files=MAX_RECIPE_FILES,
        )
    except BaseException:
        cleanup_materialized(target, tuple(copied))
        raise

    return tuple(copied)


def cleanup_materialized(target: Path, copied: tuple[MaterializedFile, ...]) -> None:
    """Remove only unchanged checkout files after a failed remote install."""

    for item in reversed(copied):
        path = target / item.path

        if path.is_file() and not path.is_symlink():
            digest, _ = digest_file(path)

            if digest == item.digest:
                path.unlink()

    for directory in sorted(
        (path for path in target.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            continue

    try:
        target.rmdir()
    except OSError:
        pass


def _validate_checkout(root: Path, tracked_files: tuple[str, ...]) -> None:
    if len(tracked_files) > MAX_RECIPE_FILES:
        raise SecurityError("recipe checkout contains too many files")

    total = 0

    for relative in tracked_files:
        safe_relative_path(relative, "recipe.checkout.path")
        path = root / relative

        if path.is_symlink() or not path.is_file():
            raise SecurityError(
                "recipe checkout may contain only regular files", path=relative
            )

        total += path.stat().st_size

        if total > MAX_RECIPE_SIZE:
            raise SecurityError("recipe checkout exceeds size limit", size=total)


def _copy_tree_files(
    source: Path,
    target: Path,
    copied: list[MaterializedFile],
    *,
    prefix: str = "",
    excluded: set[str] | None = None,
    max_size: int,
    max_files: int,
) -> None:
    excluded = excluded or set()
    count = 0
    size = 0

    for path in source.rglob("*"):
        relative = path.relative_to(source)

        if any(part in excluded for part in relative.parts):
            continue

        logical = Path(prefix) / relative if prefix else relative
        logical_path = logical.as_posix()
        safe_relative_path(logical_path, "recipe.local.path")

        if path.is_symlink():
            raise SecurityError("recipe symlinks are forbidden", path=logical_path)

        destination = target / relative

        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        if not path.is_file():
            raise SecurityError("recipe special files are forbidden", path=logical_path)

        count += 1
        size += path.stat().st_size

        if count > max_files:
            raise SecurityError("recipe contains too many files")

        if size > max_size:
            raise SecurityError("recipe exceeds size limit", size=size)

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        digest, _ = digest_file(destination)
        copied.append(MaterializedFile(logical_path, digest))


def _tracking_ref(root: Path, requested_ref: str | None) -> str | None:
    if requested_ref is None:
        symbolic = _git(
            root,
            "symbolic-ref",
            "--quiet",
            "--short",
            "refs/remotes/origin/HEAD",
            check=False,
        ).strip()
        return symbolic.removeprefix("origin/") or None

    heads = _git(
        root,
        "ls-remote",
        "--heads",
        "origin",
        requested_ref,
        check=False,
    )
    return requested_ref if heads.strip() else None


def _git(
    root: Path,
    *arguments: str,
    check: bool = True,
) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except OSError as exc:
        raise ResolutionError(f"cannot execute Git: {exc}") from exc

    if check and result.returncode != 0:
        raise ResolutionError(
            "Git recipe operation failed",
            exit_code=result.returncode,
            stderr=result.stderr[-2000:],
        )

    return result.stdout
