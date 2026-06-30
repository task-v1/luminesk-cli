from pathlib import Path

import httpx
from rich.console import Console

from luminesk.core.messages import t
from luminesk.models.registry import CoreProvider, GitHubRelease, Jenkins, Maven
from luminesk.utils import github_releases, jenkins, maven
from luminesk.utils.download_models import CoreDownloadInfo


def get_availability_check_url(core: CoreProvider) -> str:
    if isinstance(core, Maven):
        return maven.get_metadata_url(core)

    if isinstance(core, Jenkins):
        return jenkins.get_build_info_url(core)

    if isinstance(core, GitHubRelease):
        return github_releases.get_release_api_url(core)

    raise ValueError(
        t(
            "downloads.unsupported_provider_type",
            type_name=type(core).__name__,
            core_id=core.id,
        )
    )


def get_latest_download_info(
    core: CoreProvider, client: httpx.Client | None = None
) -> CoreDownloadInfo:
    if isinstance(core, Maven):
        return maven.get_latest_download_info(core, client=client)

    if isinstance(core, Jenkins):
        return jenkins.get_latest_download_info(core, client=client)

    if isinstance(core, GitHubRelease):
        return github_releases.get_latest_download_info(core, client=client)

    raise ValueError(
        t(
            "downloads.unsupported_provider_type",
            type_name=type(core).__name__,
            core_id=core.id,
        )
    )


def get_latest_download_url(
    core: CoreProvider, client: httpx.Client | None = None
) -> str:
    return get_latest_download_info(core, client=client).url


def download_url(url: str, target_path: Path, console: Console | None = None) -> None:
    import httpx
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )

    from luminesk.utils.http import stream_with_retries

    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        with stream_with_retries(client, "GET", url) as response:
            response.raise_for_status()
            try:
                total_size = int(response.headers.get("content-length", 0))
            except ValueError:
                total_size = 0
            temp_path = target_path.with_suffix(".tmp")

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=True,
            )

            with progress:
                task_id = progress.add_task(
                    f"Downloading {target_path.name}...", total=total_size or None
                )
                with temp_path.open("wb") as file:
                    for chunk in response.iter_bytes():
                        if not chunk:
                            continue

                        file.write(chunk)
                        progress.update(task_id, advance=len(chunk))

            temp_path.replace(target_path)
