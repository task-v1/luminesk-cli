"""Official Mojang Java server version resolver."""

from __future__ import annotations

from typing import Any

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import MojangVersionOptions, SourceSpec
from luminesk_cli.domain.primitives import validate_https_url
from luminesk_cli.infrastructure.sources.base import Resolution
from luminesk_cli.infrastructure.sources.common import request_json_object

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


class MojangVersionResolver:
    def resolve(self, source: SourceSpec, client: httpx.Client) -> Resolution:
        if not isinstance(source.options, MojangVersionOptions):
            raise ResolutionError("mojang-version source has invalid options")

        manifest = request_json_object(client, VERSION_MANIFEST_URL, source)
        version = _select_version(manifest, source.options.version)
        metadata_url = version.get("url")
        if not isinstance(metadata_url, str):
            raise ResolutionError("Mojang version entry has no metadata URL")
        metadata = request_json_object(client, metadata_url, source)
        downloads = metadata.get("downloads")
        server = downloads.get("server") if isinstance(downloads, dict) else None
        if not isinstance(server, dict):
            raise ResolutionError("Mojang version has no dedicated server download")
        url = server.get("url")
        size = server.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ResolutionError("Mojang server download has invalid size")

        version_id = version.get("id")
        assert isinstance(version_id, str)
        return Resolution(
            type=source.type,
            version=version_id,
            source_revision=version_id,
            url=validate_https_url(url, "mojang.server.url"),
            target=source.target,
            size=size,
            media_type="application/java-archive",
        )


def _select_version(manifest: dict[str, Any], selector: str) -> dict[str, Any]:
    selected_value: object = selector
    if selector in {"latest", "latest-release"}:
        latest = manifest.get("latest")
        selected_value = latest.get("release") if isinstance(latest, dict) else None
    elif selector == "latest-snapshot":
        latest = manifest.get("latest")
        selected_value = latest.get("snapshot") if isinstance(latest, dict) else None
    if not isinstance(selected_value, str) or not selected_value:
        raise ResolutionError("Mojang version manifest has no requested latest version")
    selected = selected_value

    versions = manifest.get("versions")
    if not isinstance(versions, list):
        raise ResolutionError("Mojang version manifest versions must be an array")
    matches = [
        item
        for item in versions
        if isinstance(item, dict) and item.get("id") == selected
    ]
    if len(matches) != 1:
        raise ResolutionError(f"Mojang version does not exist: {selected}")
    return matches[0]
