"""Selective, bounded materialization through the GitHub contents API."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from luminesk_cli.domain.errors import ResolutionError, SecurityError
from luminesk_cli.domain.manifest import SourceSpec
from luminesk_cli.domain.primitives import safe_relative_path
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.fetch import SecureFetcher
from luminesk_cli.infrastructure.sources.common import request_metadata
from luminesk_cli.infrastructure.state import atomic_write


class GitHubContentsFetcher:
    """Fetch only explicitly declared paths below one repository root."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        cache: ContentCache,
        api_root: str,
        revision: str,
        metadata_source: SourceSpec,
        root: str = "",
        headers: Mapping[str, str] | None = None,
        max_files: int,
        max_size: int,
    ) -> None:
        self.client = client
        self.cache = cache
        self.api_root = api_root.rstrip("/")
        self.revision = revision
        self.metadata_source = metadata_source
        self.root = safe_relative_path(root, "github.contents.root") if root else ""
        self.headers = dict(headers or {})
        self.max_files = max_files
        self.max_size = max_size
        self._requested: set[str] = set()
        self._files: set[str] = set()
        self._size = 0

    def fetch(self, paths: tuple[str, ...], destination: Path) -> None:
        for relative in paths:
            self._fetch_path(
                safe_relative_path(relative, "github.contents.declaredPath"),
                destination,
            )

    def _fetch_path(self, relative: str, destination: Path) -> None:
        full = f"{self.root}/{relative}" if self.root else relative
        if full in self._requested:
            return
        self._requested.add(full)
        url = f"{self.api_root}/contents/{quote(full, safe='/')}?ref={self.revision}"
        response = request_metadata(
            self.client,
            url,
            self.metadata_source,
            headers=self.headers,
        )
        try:
            value = response.json()
        except ValueError as exc:
            raise ResolutionError("GitHub contents metadata is not valid JSON") from exc
        self._materialize(value, full, destination)

    def _materialize(
        self,
        value: Any,
        requested: str,
        destination: Path,
    ) -> None:
        items = value if isinstance(value, list) else [value]
        if not all(isinstance(item, dict) for item in items):
            raise ResolutionError("GitHub contents metadata has an invalid shape")

        for item in items:
            item_type = item.get("type")
            raw_path = item.get("path")
            if not isinstance(raw_path, str):
                raise ResolutionError("GitHub contents entry has no path")
            full_path = safe_relative_path(raw_path, "github.contents.path")
            if full_path != requested and not full_path.startswith(f"{requested}/"):
                raise SecurityError("GitHub contents entry escapes its declared path")
            prefix = f"{self.root}/" if self.root else ""
            if prefix and not full_path.startswith(prefix):
                raise SecurityError("GitHub contents entry escapes its recipe root")
            relative = full_path.removeprefix(prefix)
            target = destination / relative

            if item_type == "dir":
                target.mkdir(parents=True, exist_ok=True)
                self._fetch_path(relative, destination)
                continue
            if item_type != "file":
                raise SecurityError(
                    "GitHub recipe symlinks and special entries are forbidden"
                )

            size = item.get("size")
            download_url = item.get("download_url")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise ResolutionError("GitHub contents file has an invalid size")
            if not isinstance(download_url, str):
                raise ResolutionError("GitHub contents file has no download URL")
            if relative in self._files:
                continue
            self._files.add(relative)
            self._size += size
            if len(self._files) > self.max_files:
                raise SecurityError("GitHub recipe contains too many files")
            if self._size > self.max_size:
                raise SecurityError("GitHub recipe exceeds total size limit")

            blob = SecureFetcher(self.cache, client=self.client).fetch(
                download_url,
                max_size=min(self.max_size, max(size, 1)),
                expected_size=size,
                allow_private_network=self.metadata_source.allow_private_network,
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(target, blob.path.read_bytes())
