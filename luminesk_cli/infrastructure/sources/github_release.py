"""GitHub Release source adapter."""

from __future__ import annotations

import fnmatch
import os
from typing import Any

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import SourceSpec
from luminesk_cli.domain.primitives import validate_digest, validate_https_url
from luminesk_cli.infrastructure.sources.base import Resolution
from luminesk_cli.infrastructure.sources.common import (
    request_json_object,
    request_metadata,
    select_highest_version,
)


class GitHubReleaseResolver:
    def resolve(self, source: SourceSpec, client: httpx.Client) -> Resolution:
        if source.repository is None or source.asset is None:
            raise ResolutionError("github-release requires repository and asset")

        owner, repository = _parse_repository(source.repository)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "nesk/2",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.environ.get("GITHUB_TOKEN")

        if token:
            headers["Authorization"] = f"Bearer {token}"

        api_root = f"https://api.github.com/repos/{owner}/{repository}/releases"

        if source.version in {None, "", "latest", "*"} and source.channel == "stable":
            release = request_json_object(
                client, f"{api_root}/latest", source, headers=headers
            )
        elif source.version is not None and not any(
            symbol in source.version for symbol in "<>=,*"
        ):
            release = request_json_object(
                client,
                f"{api_root}/tags/{source.version}",
                source,
                headers=headers,
            )
        else:
            response = request_metadata(
                client,
                f"{api_root}?per_page=100",
                source,
                headers=headers,
            )
            payload = response.json()

            if not isinstance(payload, list):
                raise ResolutionError("GitHub releases response must be an array")

            releases = [
                item
                for item in payload
                if isinstance(item, dict)
                and not item.get("draft", False)
                and (source.channel != "stable" or not item.get("prerelease", False))
                and isinstance(item.get("tag_name"), str)
            ]
            selected_tag = select_highest_version(
                [item["tag_name"] for item in releases],
                source.version,
                source.channel,
            )
            release = next(
                item for item in releases if item["tag_name"] == selected_tag
            )

        return _resolution_from_release(source, release)


def _parse_repository(value: str) -> tuple[str, str]:
    normalized = value.strip().removesuffix(".git").strip("/")

    if normalized.startswith("https://github.com/"):
        normalized = normalized.removeprefix("https://github.com/")

    parts = normalized.split("/")

    if len(parts) != 2 or not all(parts):
        raise ResolutionError("GitHub repository must be OWNER/REPO")

    return parts[0], parts[1]


def _select_asset(assets: Any, pattern: str) -> dict[str, Any]:
    if not isinstance(assets, list):
        raise ResolutionError("GitHub release assets must be an array")

    matches = []

    for raw_asset in assets:
        if not isinstance(raw_asset, dict):
            continue

        name = raw_asset.get("name")
        url = raw_asset.get("browser_download_url")

        if (
            isinstance(name, str)
            and isinstance(url, str)
            and fnmatch.fnmatch(name, pattern)
        ):
            matches.append(raw_asset)

    if not matches:
        raise ResolutionError(f"no GitHub release asset matches {pattern}")

    if len(matches) != 1:
        raise ResolutionError(
            f"GitHub release asset pattern {pattern} is ambiguous",
            count=len(matches),
        )

    return matches[0]


def _resolution_from_release(source: SourceSpec, release: dict[str, Any]) -> Resolution:
    asset = _select_asset(release.get("assets"), source.asset or "")
    tag = release.get("tag_name")
    url = asset.get("browser_download_url")
    size = asset.get("size")

    if not isinstance(tag, str) or not tag:
        raise ResolutionError("GitHub release has no tag_name")

    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ResolutionError("GitHub release asset has invalid size")

    digest = asset.get("digest")

    if digest is not None:
        digest = validate_digest(digest, "github.asset.digest")

    return Resolution(
        provider=source.provider,
        version=tag.lstrip("v"),
        source_revision=tag,
        url=validate_https_url(url, "github.asset.url"),
        target=source.target,
        size=size,
        digest=digest,
        media_type=(
            asset.get("content_type")
            if isinstance(asset.get("content_type"), str)
            else None
        ),
    )
