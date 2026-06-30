from __future__ import annotations

import fnmatch
from typing import Any

import httpx

from luminesk.core.messages import t
from luminesk.models.registry import GitHubRelease
from luminesk.utils.download_models import CoreDownloadInfo
from luminesk.utils.errors import format_error
from luminesk.utils.http import get_json_object_with_retries


def get_release_api_url(core: GitHubRelease) -> str:
    owner, repo = parse_github_repo_url(core.url)
    return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"


def get_latest_download_url(
    core: GitHubRelease, client: httpx.Client | None = None
) -> str:
    return get_latest_download_info(core, client=client).url


def get_latest_download_info(
    core: GitHubRelease,
    client: httpx.Client | None = None,
) -> CoreDownloadInfo:
    if client is not None:
        return _get_latest_download_info(client, core)

    with httpx.Client(timeout=10.0, follow_redirects=True) as owned_client:
        return _get_latest_download_info(owned_client, core)


def _get_latest_download_info(
    client: httpx.Client,
    core: GitHubRelease,
) -> CoreDownloadInfo:
    release = fetch_json(client, get_release_api_url(core))
    assets = release.get("assets")

    if not isinstance(assets, list) or not assets:
        raise ValueError(t("github.assets_missing", core_id=core.id))

    asset = select_asset(assets, core.release_file)
    digest = asset.get("digest", "")

    if isinstance(digest, str) and digest.startswith("sha256:"):
        digest = digest.removeprefix("sha256:")
    elif not digest:
        import hashlib
        digest = hashlib.sha256(str(asset.get("id")).encode()).hexdigest()

    return CoreDownloadInfo(
        url=asset["browser_download_url"],
        hash=digest,
    )


def fetch_json(client: httpx.Client, url: str) -> dict[str, Any]:
    import os

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "luminesk",
    }
    token = os.environ.get("GITHUB_TOKEN")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        return get_json_object_with_retries(client, url, headers=headers)

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            is_rate_limit = False

            if exc.response.headers.get("x-ratelimit-remaining") == "0":
                is_rate_limit = True

            else:
                try:
                    body = exc.response.json()

                    if (
                        isinstance(body, dict)
                        and "rate limit" in body.get("message", "").lower()
                    ):
                        is_rate_limit = True

                except Exception:
                    if "rate limit" in exc.response.text.lower():
                        is_rate_limit = True

            if is_rate_limit:
                raise ValueError(t("github.rate_limit_exceeded")) from exc

        raise ValueError(
            t(
                "github.fetch_release_http",
                url=url,
                status_code=exc.response.status_code,
            )
        ) from exc

    except httpx.RequestError as exc:
        raise ValueError(
            t("github.fetch_release_error", url=url, error=format_error(exc))
        ) from exc

    except ValueError as exc:
        raise ValueError(t("github.invalid_json", url=url)) from exc


def select_asset(assets: list[Any], pattern: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []

    for asset in assets:
        if not isinstance(asset, dict):
            continue

        name = asset.get("name")
        download_url = asset.get("browser_download_url")

        if not isinstance(name, str) or not isinstance(download_url, str):
            continue

        if fnmatch.fnmatch(name, pattern):
            matches.append(asset)

    if not matches:
        raise ValueError(t("github.asset_missing", pattern=pattern))

    if len(matches) > 1:
        raise ValueError(
            t("github.asset_ambiguous", pattern=pattern, count=len(matches))
        )

    return matches[0]


def parse_github_repo_url(url: str) -> tuple[str, str]:
    normalized_url = url.strip().rstrip("/")
    prefix = "https://github.com/"

    if not normalized_url.startswith(prefix):
        raise ValueError(t("github.invalid_url", url=url))

    path = normalized_url.removeprefix(prefix)
    parts = [part for part in path.split("/") if part]

    if len(parts) < 2:
        raise ValueError(t("github.invalid_url", url=url))

    return parts[0], parts[1]


def get_release_asset_info(
    client: httpx.Client,
    repo_url: str,
    asset_pattern: str,
    tag: str = "latest",
) -> tuple[str, str]:
    owner, repo = parse_github_repo_url(repo_url)

    if tag == "latest":
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    else:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"

    release = fetch_json(client, api_url)
    assets = release.get("assets")

    if not isinstance(assets, list) or not assets:
        raise ValueError(t("github.assets_missing", core_id=repo))

    asset = select_asset(assets, asset_pattern)
    digest = asset.get("digest", "")

    if isinstance(digest, str) and digest.startswith("sha256:"):
        digest = digest.removeprefix("sha256:")
    elif not digest:
        import hashlib
        digest = hashlib.sha256(str(asset.get("id")).encode()).hexdigest()

    return asset["browser_download_url"], digest
