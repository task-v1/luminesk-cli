from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from luminesk_cli.application.locking import LockService
from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import SourceSpec, parse_manifest
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.sources.common import (
    select_highest_version,
    version_matches,
)
from luminesk_cli.infrastructure.sources.github_release import (
    GitHubReleaseResolver,
)


def test_semver_constraints_and_stable_channel() -> None:
    versions = ["v1.9.0", "v2.0.0-beta.1", "v2.0.0", "v3.0.0"]

    assert version_matches("v2.0.0", ">=2.0.0,<3.0.0", "stable")
    assert not version_matches("v2.0.0-beta.1", None, "stable")
    assert select_highest_version(versions, ">=1.0.0,<3.0.0", "stable") == "v2.0.0"


def test_github_release_requires_unambiguous_asset() -> None:
    payload = {
        "tag_name": "v2.1.0",
        "assets": [
            {
                "name": "server.jar",
                "browser_download_url": "https://objects.example/server.jar",
                "size": 4,
            },
            {
                "name": "server-slim.jar",
                "browser_download_url": "https://objects.example/server-slim.jar",
                "size": 4,
            },
        ],
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )
    source = SourceSpec(
        id="core",
        provider="github-release",
        repository="owner/repo",
        asset="server*.jar",
        target="server.jar",
        allow_private_network=True,
    )

    with pytest.raises(ResolutionError, match="ambiguous"):
        GitHubReleaseResolver().resolve(source, client)


def test_local_source_lock_has_real_digest(tmp_path: Path) -> None:
    artifact = tmp_path / "fixture.jar"
    artifact.write_bytes(b"server")
    manifest = parse_manifest(
        b"""\
manifest_version = 1
[package]
name = "local-server"
version = "1.0.0"
[[sources]]
id = "core"
provider = "local-file"
path = "fixture.jar"
target = "server.jar"
[runtime]
driver = "docker"
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["./server.jar"]
"""
    )
    service = LockService(
        ContentCache(tmp_path / "cache"),
        image_resolver=OciImageResolver(),
    )

    lockfile = service.create(manifest, tmp_path, target="linux/amd64")

    assert lockfile.sources["core"].url == "local:fixture.jar"
    assert lockfile.sources["core"].digest.startswith("sha256:")
    assert lockfile.runtime.image == manifest.runtime.image
