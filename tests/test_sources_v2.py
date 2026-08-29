from __future__ import annotations

import subprocess
from pathlib import Path

import httpx
import pytest

from luminesk_cli.application.locking import LockService
from luminesk_cli.domain.errors import NetworkError, ResolutionError
from luminesk_cli.domain.manifest import SourceSpec, parse_manifest
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.sources.common import (
    MAX_METADATA_SIZE,
    request_metadata,
    select_highest_version,
    version_matches,
)
from luminesk_cli.infrastructure.sources.github_release import (
    GitHubReleaseResolver,
)
from luminesk_cli.infrastructure.sources.jenkins import JenkinsResolver
from luminesk_cli.infrastructure.sources.maven import MavenResolver


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


def test_github_release_selects_highest_matching_release() -> None:
    releases = [
        {
            "tag_name": "v2.0.1",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": "server.jar",
                    "browser_download_url": "https://objects.example/server.jar",
                    "size": 6,
                    "digest": f"sha256:{'a' * 64}",
                    "content_type": "application/java-archive",
                }
            ],
        },
        {
            "tag_name": "v2.1.0-beta.1",
            "draft": False,
            "prerelease": True,
            "assets": [],
        },
        {"tag_name": "v2.2.0", "draft": True, "assets": []},
    ]
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=releases)

    source = SourceSpec(
        id="core",
        provider="github-release",
        repository="https://github.com/owner/repository.git",
        version=">=2.0.0,<3.0.0",
        asset="server.jar",
        target="server.jar",
        allow_private_network=True,
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = GitHubReleaseResolver().resolve(source, client)

    assert requests[0].url.path.endswith("/releases")
    assert requests[0].url.params["per_page"] == "100"
    assert result.version == "2.0.1"
    assert result.digest == f"sha256:{'a' * 64}"
    assert result.media_type == "application/java-archive"


def test_jenkins_resolution_uses_immutable_revision() -> None:
    metadata = {
        "number": 42,
        "actions": [{"lastBuiltRevision": {"SHA1": " AABBCC "}}],
        "artifacts": [
            {
                "fileName": "server.jar",
                "relativePath": "build/server.jar",
                "fileSize": 128,
            }
        ],
    }
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=metadata)
        )
    )
    source = SourceSpec(
        id="core",
        provider="jenkins",
        url="https://ci.example",
        job="server/main",
        build=42,
        asset="*.jar",
        target="server.jar",
        allow_private_network=True,
    )

    result = JenkinsResolver().resolve(source, client)

    assert result.version == "42"
    assert result.source_revision == "aabbcc"
    assert result.url.endswith("/42/artifact/build/server.jar")
    assert result.size == 128
    assert result.media_type == "application/java-archive"


def test_maven_release_resolution_reads_optional_sha256() -> None:
    digest = "b" * 64

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("maven-metadata.xml"):
            return httpx.Response(
                200,
                content=b"""\
<metadata><versioning><versions>
<version>2.0.0</version><version>2.3.0</version><version>3.0.0</version>
</versions></versioning></metadata>
""",
            )

        assert request.url.path.endswith("server-2.3.0.jar.sha256")
        return httpx.Response(200, text=f"{digest}  server-2.3.0.jar")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = SourceSpec(
        id="core",
        provider="maven",
        repository="https://repo.example/releases",
        group="org.example",
        artifact="server",
        version=">=2.0.0,<3.0.0",
        target="server.jar",
        allow_private_network=True,
    )

    result = MavenResolver().resolve(source, client)

    assert result.version == "2.3.0"
    assert result.source_revision == "2.3.0"
    assert result.url.endswith("/server/2.3.0/server-2.3.0.jar")
    assert result.digest == f"sha256:{digest}"


def test_maven_snapshot_resolution_uses_timestamped_artifact() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1

        if calls == 1:
            return httpx.Response(
                200,
                content=b"""\
<metadata><versioning><versions>
<version>2.4.0-SNAPSHOT</version>
</versions></versioning></metadata>
""",
            )

        if calls == 2:
            return httpx.Response(
                200,
                content=b"""\
<metadata><version>2.4.0-SNAPSHOT</version><versioning>
<snapshotVersions><snapshotVersion><extension>jar</extension>
<classifier>all</classifier><value>2.4.0-20260830.010203-7</value>
</snapshotVersion></snapshotVersions></versioning></metadata>
""",
            )

        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = SourceSpec(
        id="core",
        provider="maven",
        repository="https://repo.example/snapshots",
        group="org.example",
        artifact="server",
        version="2.4.0-SNAPSHOT",
        classifier="all",
        target="server.jar",
        allow_private_network=True,
    )

    result = MavenResolver().resolve(source, client)

    assert result.source_revision == "2.4.0-20260830.010203-7"
    assert result.url.endswith("server-2.4.0-20260830.010203-7-all.jar")
    assert result.digest is None


def test_metadata_redirect_drops_credentials_on_host_change() -> None:
    seen_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)

        if request.url.host == "api.example":
            return httpx.Response(
                302,
                headers={"location": "https://cdn.example/metadata.json"},
            )

        return httpx.Response(200, json={"version": "2.0.0"})

    source = SourceSpec(
        id="metadata",
        provider="http",
        target="metadata.json",
        allow_private_network=True,
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    response = request_metadata(
        client,
        "https://api.example/metadata.json",
        source,
        headers={"authorization": "Bearer secret", "Cookie": "token=secret"},
    )

    assert response.json() == {"version": "2.0.0"}
    assert "authorization" in seen_headers[0]
    assert "cookie" in seen_headers[0]
    assert "authorization" not in seen_headers[1]
    assert "cookie" not in seen_headers[1]


def test_metadata_body_is_bounded_while_streaming() -> None:
    source = SourceSpec(
        id="metadata",
        provider="http",
        target="metadata.json",
        allow_private_network=True,
    )
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"x" * (MAX_METADATA_SIZE + 1))
        )
    )

    with pytest.raises(ResolutionError, match="too large"):
        request_metadata(client, "https://api.example/metadata.json", source)


def test_metadata_http_failures_have_stable_network_error() -> None:
    source = SourceSpec(
        id="metadata",
        provider="http",
        target="metadata.json",
        allow_private_network=True,
    )
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    )

    with pytest.raises(NetworkError, match="HTTP 503"):
        request_metadata(client, "https://api.example/metadata.json", source)


def test_oci_resolver_pulls_and_selects_matching_repository_digest() -> None:
    calls: list[list[str]] = []

    def runner(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(argv)

        if argv[1:3] == ["image", "inspect"] and len(calls) == 1:
            return subprocess.CompletedProcess(argv, 1, "", "missing")

        if argv[1] == "pull":
            return subprocess.CompletedProcess(argv, 0, "", "")

        return subprocess.CompletedProcess(
            argv,
            0,
            f'["other/image@sha256:{"c" * 64}",'
            f'"registry.example/team/server@sha256:{"d" * 64}"]',
            "",
        )

    result = OciImageResolver(runner).resolve("registry.example/team/server:2.0")

    assert result == f"registry.example/team/server@sha256:{'d' * 64}"
    assert calls[1] == ["docker", "pull", "registry.example/team/server:2.0"]


@pytest.mark.parametrize(
    "image",
    [
        "server@sha256:short",
        f"server@sha256:{'A' * 64}",
        f"server@sha256:{'a' * 64}:latest",
    ],
)
def test_oci_resolver_rejects_malformed_digest_pins(image: str) -> None:
    with pytest.raises(ResolutionError, match="digest is invalid"):
        OciImageResolver().resolve(image)
