import httpx
import pytest

from luminesk.models.registry import GitHubRelease
from luminesk.utils import github_releases
from luminesk.utils.download_models import CoreDownloadInfo


def test_parse_github_repo_url() -> None:
    assert github_releases.parse_github_repo_url("https://github.com/owner/repo") == (
        "owner",
        "repo",
    )
    assert github_releases.parse_github_repo_url("https://github.com/owner/repo/") == (
        "owner",
        "repo",
    )

    with pytest.raises(ValueError, match="Invalid GitHub URL"):
        github_releases.parse_github_repo_url("https://notgithub.com/owner/repo")

    with pytest.raises(ValueError, match="Invalid GitHub URL"):
        github_releases.parse_github_repo_url("https://github.com/owner")


def test_get_release_api_url() -> None:
    core = GitHubRelease(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://github.com/my-owner/my-repo",
        release_file="Lumi-*.jar",
    )
    assert (
        github_releases.get_release_api_url(core)
        == "https://api.github.com/repos/my-owner/my-repo/releases/latest"
    )


def test_select_asset() -> None:
    assets = [
        {"name": "readme.txt", "browser_download_url": "http://download/readme.txt"},
        {
            "name": "Lumi-1.0.jar",
            "browser_download_url": "http://download/Lumi-1.0.jar",
        },
        {
            "name": "Lumi-1.0-shaded.jar",
            "browser_download_url": "http://download/Lumi-1.0-shaded.jar",
        },
    ]

    # exact match
    assert (
        github_releases.select_asset(assets, "Lumi-1.0.jar")
        == assets[1]
    )
    # glob match
    assert (
        github_releases.select_asset(assets, "*shaded.jar")
        == assets[2]
    )

    # missing match
    with pytest.raises(ValueError, match="No GitHub release asset matched pattern"):
        github_releases.select_asset(assets, "missing-file.jar")

    # ambiguous match
    with pytest.raises(ValueError, match="is ambiguous: found 2 matches"):
        github_releases.select_asset(assets, "Lumi-*.jar")


def test_github_releases_rate_limiting() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0"},
            json={"message": "API rate limit exceeded for ..."},
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    core = GitHubRelease(
        id="lumi",
        name="Lumi",
        description={"en": "desc"},
        url="https://github.com/example/repo",
        release_file="Lumi-*.jar",
    )

    with pytest.raises(ValueError, match="GitHub API rate limit exceeded"):
        github_releases._get_latest_download_info(client, core)


def test_get_latest_download_info_success() -> None:
    core = GitHubRelease(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://github.com/my-owner/my-repo",
        release_file="Lumi-*.jar",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "tag_name": "v2.0.0",
            "assets": [
                {
                    "name": "Lumi-2.0.0.jar",
                    "browser_download_url": "https://github.com/my-owner/my-repo/releases/download/v2.0.0/Lumi-2.0.0.jar",
                    "digest": "sha256:abcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd",
                }
            ],
        }
        return httpx.Response(200, json=payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    info = github_releases.get_latest_download_info(core, client=client)

    assert isinstance(info, CoreDownloadInfo)
    assert info.hash == "abcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd"
    assert (
        info.url
        == "https://github.com/my-owner/my-repo/releases/download/v2.0.0/Lumi-2.0.0.jar"
    )


def test_get_latest_download_url_helper() -> None:
    core = GitHubRelease(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://github.com/my-owner/my-repo",
        release_file="Lumi-*.jar",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "tag_name": "v2.0.0",
            "assets": [
                {
                    "name": "Lumi-2.0.0.jar",
                    "browser_download_url": "https://github.com/my-owner/my-repo/releases/download/v2.0.0/Lumi-2.0.0.jar",
                    "digest": "sha256:abcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd",
                }
            ],
        }
        return httpx.Response(200, json=payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    url = github_releases.get_latest_download_url(core, client=client)
    assert (
        url
        == "https://github.com/my-owner/my-repo/releases/download/v2.0.0/Lumi-2.0.0.jar"
    )


def test_get_release_asset_info() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "tag_name": "v2.0.0",
            "assets": [
                {
                    "name": "Lumi-2.0.0.jar",
                    "browser_download_url": "https://github.com/my-owner/my-repo/releases/download/v2.0.0/Lumi-2.0.0.jar",
                    "digest": "sha256:abcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd",
                }
            ],
        }
        return httpx.Response(200, json=payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    url, digest = github_releases.get_release_asset_info(
        client, "https://github.com/my-owner/my-repo", "Lumi-*.jar", tag="v2.0.0"
    )
    assert url == "https://github.com/my-owner/my-repo/releases/download/v2.0.0/Lumi-2.0.0.jar"
    assert digest == "abcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd"

