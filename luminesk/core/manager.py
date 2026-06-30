from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import signal
import subprocess
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from luminesk.core import launcher
from luminesk.core.base import BaseCore
from luminesk.core.config import CORE_CACHE_DIR, ManagedServer, UserConfig, utc_now
from luminesk.core.messages import t
from luminesk.core.registry import registry
from luminesk.models.manager import (
    CachedCorePaths,
    DownloadedCore,
    ResolvedServerTarget,
    ServerManagerError,
    ServerRuntimeView,
    ServerSignalResult,
)
from luminesk.models.registry import CoreProvider, GitHubRelease
from luminesk.utils.docker import (
    DEFAULT_DOCKER_MEMORY_LIMIT,
    DEFAULT_FALLBACK_IMAGE,
    docker_container_is_running,
    get_docker_container_exit_code,
    get_docker_container_pid,
    kill_docker_container,
    remove_docker_container,
    send_docker_ctrl_c,
    stop_docker_container,
)
from luminesk.utils.download_models import CoreDownloadInfo
from luminesk.utils.downloads import get_latest_download_info
from luminesk.utils.errors import format_error
from luminesk.utils.http import stream_with_retries
from luminesk.utils.rich_utils import (
    accent,
    ansi_text,
    format_kv,
    format_server,
    info_panel,
    muted,
    success,
    success_panel,
    warning,
)

MAX_CORE_DOWNLOAD_BYTES = 512 * 1024 * 1024
SHA256_HEX_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
CORE_DOWNLOAD_TIMEOUT = httpx.Timeout(
    timeout=30.0,
    connect=10.0,
    read=30.0,
    write=30.0,
    pool=10.0,
)


STOP_SIGNAL = int(getattr(signal, "SIGINT", 2))
KILL_SIGNAL = 9


def create_server(
    config: UserConfig,
    name: str,
    tag: str,
    directory: Path,
    core: BaseCore,
    force: bool = False,
    console: Console | None = None,
    memory_limit: str | None = None,
    runtime_image: str | None = None,
) -> ManagedServer:
    normalized_directory = directory.expanduser().resolve()
    _ensure_registration_target_available(config, tag, normalized_directory)

    prepare_server_directory(normalized_directory, force=force)

    if not getattr(core, "dont_create_config", False):
        ensure_server_config_file(normalized_directory, core.config_file)

    downloaded_core_maybe = download_core(core, normalized_directory, console=console)
    assert downloaded_core_maybe is not None
    downloaded_core = downloaded_core_maybe

    server = ManagedServer(
        name=name,
        tag=tag,
        path=normalized_directory,
        core_id=core.id,
        core_hash=downloaded_core.hash,
        config_file=core.config_file,
        port_way=core.port_way,
        executable_name=str(
            downloaded_core.executable_path.relative_to(normalized_directory)
        ),
        runtime_image=runtime_image or DEFAULT_FALLBACK_IMAGE,
        memory_limit=memory_limit or DEFAULT_DOCKER_MEMORY_LIMIT,
    )
    config.register_server(server)
    config.save()
    return server


def prepare_server_directory(directory: Path, force: bool = False) -> Path:
    if directory.exists():
        if not directory.is_dir():
            if not force:
                raise ServerManagerError(
                    t("manager.path_exists_not_directory", directory=directory)
                )

            directory.unlink()
        elif any(directory.iterdir()):
            if not force:
                raise ServerManagerError(
                    t("manager.directory_not_empty", directory=directory)
                )

            shutil.rmtree(directory)

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_server_config_file(directory: Path, config_file_name: str) -> Path:
    config_file_path = directory / config_file_name

    if not config_file_path.exists():
        config_file_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = config_file_path.suffix.lower()
        if suffix in {".yml", ".yaml", ".json"}:
            content = "{}"
        elif suffix == ".toml":
            content = ""
        else:
            content = t("manager.server_config_header")
        config_file_path.write_text(
            content,
            encoding="utf-8",
        )

    return config_file_path


def download_core(
    core: BaseCore,
    target_directory: Path,
    console: Console | None = None,
    skip_if_hash: str | None = None,
) -> DownloadedCore | None:
    return core.download(target_directory, console, skip_if_hash)


def download_core_raw(
    core: CoreProvider,
    target_directory: Path,
    console: Console | None = None,
    skip_if_hash: str | None = None,
) -> DownloadedCore | None:
    target_directory.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=CORE_DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
        download_info = get_latest_download_info(core, client=client)
        if skip_if_hash is not None and download_info.hash == skip_if_hash:
            return None

        expected_hash = download_info.hash

        cached_core = _restore_cached_core(
            core=core,
            download_info=download_info,
            target_directory=target_directory,
            expected_hash=expected_hash,
            console=console,
        )
        if cached_core is not None:
            return cached_core

        temp_path: Path | None = None
        try:
            with stream_with_retries(client, "GET", download_info.url) as response:
                file_name = _resolve_download_file_name(
                    response, download_info.url, core
                )
                target_path = _resolve_download_target_path(target_directory, file_name)
                temp_path = _get_temporary_file_path(target_path)
                total_size = _parse_content_length(
                    response.headers.get("content-length")
                )
                _validate_download_size(total_size)
                bytes_downloaded = 0
                if expected_hash and len(expected_hash) == 40:
                    hash_obj = hashlib.sha1()
                else:
                    hash_obj = hashlib.sha256()

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
                        t("manager.download_progress", core_name=core.name),
                        total=total_size,
                    )
                    with temp_path.open("wb") as file:
                        for chunk in response.iter_bytes():
                            if not chunk:
                                continue

                            bytes_downloaded += len(chunk)
                            _validate_download_size(bytes_downloaded)
                            hash_obj.update(chunk)
                            file.write(chunk)
                            progress.update(task_id, advance=len(chunk))

                actual_hash = hash_obj.hexdigest()
                if expected_hash is not None and not hmac.compare_digest(
                    actual_hash.lower(), expected_hash.lower()
                ):
                    _cleanup_path(temp_path)
                    raise ServerManagerError(
                        t(
                            "manager.download_sha256_mismatch",
                            expected_sha256=expected_hash,
                            actual_sha256=actual_hash,
                        )
                    )

                temp_path.replace(target_path)
                _store_core_in_cache(
                    core, download_info, target_path, expected_hash or actual_hash
                )
                return DownloadedCore(
                    executable_path=target_path, hash=expected_hash or actual_hash
                )
        except ServerManagerError:
            if temp_path is not None:
                _cleanup_path(temp_path)
            raise
        except httpx.HTTPStatusError as exc:
            raise ServerManagerError(
                t(
                    "manager.download_core_http",
                    core_name=core.name,
                    status_code=exc.response.status_code,
                )
            ) from exc
        except httpx.RequestError as exc:
            raise ServerManagerError(
                t(
                    "manager.download_core_error",
                    core_name=core.name,
                    error=format_error(exc),
                )
            ) from exc


def resolve_server(
    config: UserConfig,
    tag: str | None = None,
    directory: Path | None = None,
) -> ManagedServer:
    if tag:
        server = config.get_server_by_tag(tag)
        if server is None:
            raise ServerManagerError(t("manager.server_not_found_by_tag", tag=tag))
        return server

    search_directory = (directory or Path.cwd()).expanduser().resolve()
    server = config.get_server_by_directory(search_directory)

    if server is None:
        raise ServerManagerError(
            t("manager.server_not_found_for_directory", directory=search_directory)
        )

    return server


def resolve_server_target(
    config: UserConfig,
    tag: str | None = None,
    directory: Path | None = None,
) -> ResolvedServerTarget:
    sync_runtime_states(config)

    if not tag or not tag.strip():
        server = resolve_server(config=config, tag=None, directory=directory)
        return ResolvedServerTarget(
            server=server,
            value=server.tag,
        )

    normalized_target = tag.strip()
    server = config.get_server_by_tag(normalized_target)

    if server is not None:
        return ResolvedServerTarget(
            server=server,
            value=normalized_target,
        )

    if normalized_target.isdigit():
        server = _find_server_by_pid(config, int(normalized_target))
        if server is None:
            raise ServerManagerError(t("manager.pid_not_owned", pid=normalized_target))
        return ResolvedServerTarget(
            server=server,
            value=normalized_target,
        )

    raise ServerManagerError(
        t("manager.server_not_found_by_tag", tag=normalized_target)
    )


def sync_runtime_states(config: UserConfig) -> bool:
    changed = False

    for server in config.get_servers():
        server_pid_alive = _is_server_runtime_alive(server)
        loop_active = bool(server.runtime.loop_enabled and server_pid_alive)

        if server_pid_alive:
            changed = _sync_docker_runtime_pid(server) or changed
            continue

        if loop_active:
            continue

        if (
            server.runtime.status != "stopped"
            or server.runtime.pid is not None
            or server.runtime.loop_enabled
            or server.runtime.docker_container_name is not None
        ):
            exit_code = _get_runtime_exit_code(server)
            _cleanup_stopped_docker_runtime(server)
            config.mark_server_stopped(server.tag, exit_code=exit_code)
            changed = True

    if changed:
        config.save()

    return changed


def get_runtime_view(config: UserConfig, server: ManagedServer) -> ServerRuntimeView:
    sync_runtime_states(config)
    return _build_runtime_view(config, server)


def get_runtime_views(config: UserConfig) -> list[ServerRuntimeView]:
    sync_runtime_states(config)
    return [_build_runtime_view(config, server) for server in config.get_servers()]


def _build_runtime_view(config: UserConfig, server: ManagedServer) -> ServerRuntimeView:
    fresh_server = config.get_server_by_tag(server.tag) or server
    is_running = fresh_server.runtime.status == "running" and _is_server_runtime_alive(
        fresh_server
    )
    loop_active = bool(fresh_server.runtime.loop_enabled and is_running)
    uptime = _get_uptime(fresh_server) if is_running else None
    docker_container_name = (
        _get_active_docker_container_name(fresh_server) if is_running else None
    )

    return ServerRuntimeView(
        server=fresh_server,
        status="running" if is_running else "stopped",
        pid=fresh_server.runtime.pid if is_running else None,
        loop_enabled=loop_active,
        docker_container_name=docker_container_name,
        uptime=uptime,
        last_started_at=fresh_server.runtime.last_started_at,
        last_stopped_at=fresh_server.runtime.last_stopped_at,
        last_exit_code=fresh_server.runtime.last_exit_code,
    )


def stop_server(
    config: UserConfig,
    tag: str | None = None,
    force: bool = False,
    directory: Path | None = None,
) -> ServerSignalResult:
    return send_signal_to_server(
        config=config,
        tag=tag,
        sig=STOP_SIGNAL,
        force=force,
        directory=directory,
    )


def kill_server(
    config: UserConfig,
    tag: str | None = None,
    force: bool = False,
    directory: Path | None = None,
) -> ServerSignalResult:
    return send_signal_to_server(
        config=config,
        tag=tag,
        sig=KILL_SIGNAL,
        force=force,
        directory=directory,
    )


def send_signal_to_server(
    config: UserConfig,
    tag: str | None,
    sig: int,
    force: bool = False,
    directory: Path | None = None,
) -> ServerSignalResult:
    resolved_target = resolve_server_target(config, tag, directory=directory)
    server = (
        config.get_server_by_tag(resolved_target.server.tag) or resolved_target.server
    )
    server_pid_alive = _is_server_runtime_alive(server)
    loop_active = bool(server.runtime.loop_enabled and server_pid_alive)

    if not server_pid_alive and not loop_active:
        raise ServerManagerError(t("manager.server_not_running", tag=server.tag))

    signaled_server = False
    docker_container_name = server.runtime.docker_container_name

    if docker_container_name is not None:
        try:
            if _is_kill_signal(sig):
                kill_docker_container(docker_container_name)
                signaled_server = True
            else:
                if loop_active and not force:
                    send_docker_ctrl_c(docker_container_name)
                    signaled_server = True
                else:
                    _stop_docker_server_gracefully(docker_container_name, force=force)
                    signaled_server = True
        except RuntimeError as exc:
            raise ServerManagerError(str(exc)) from exc

        if not (loop_active and not force):
            exit_code = get_docker_container_exit_code(docker_container_name)
            remove_docker_container(docker_container_name)
            config.mark_server_stopped(server.tag, exit_code=exit_code)
            config.save()

        return ServerSignalResult(
            target=resolved_target,
            signal_name=_get_signal_name(sig),
            server_pid=server.runtime.pid,
            loop_active=loop_active,
            signaled_server=signaled_server,
        )

    if force and loop_active:
        controller_pid = _get_parent_pid(server.runtime.pid)
        if controller_pid is None:
            raise ServerManagerError(
                t("manager.loop_controller_not_found", tag=server.tag)
            )
        _send_signal(controller_pid, sig)

    if server_pid_alive:
        _send_signal(server.runtime.pid, sig)
        signaled_server = True
    elif loop_active and not force:
        raise ServerManagerError(t("manager.loop_waiting_force", tag=server.tag))

    return ServerSignalResult(
        target=resolved_target,
        signal_name=_get_signal_name(sig),
        server_pid=server.runtime.pid if server_pid_alive else None,
        loop_active=loop_active,
        signaled_server=signaled_server,
    )


def upgrade_server_core(
    config: UserConfig,
    server: ManagedServer,
    console: Console | None = None,
    redownload: bool = False,
) -> tuple[ManagedServer, bool]:
    resolved_server = _ensure_server_can_modify_core(config, server)

    if resolved_server.core_hash is None and not redownload:
        raise ServerManagerError(
            t("manager.missing_core_hash_suggest_redownload", tag=resolved_server.tag)
        )

    core = registry.get_by_id(resolved_server.core_id)

    if core is None:
        raise ServerManagerError(
            t("manager.core_not_in_registry", core_id=resolved_server.core_id)
        )

    downloaded_core = download_core(
        core,
        resolved_server.path,
        console=console,
        skip_if_hash=None if redownload else resolved_server.core_hash,
    )

    if downloaded_core is None:
        return resolved_server, False

    _remove_previous_managed_executable(
        resolved_server, downloaded_core.executable_path
    )
    resolved_server.core_hash = downloaded_core.hash
    resolved_server.executable_name = str(
        downloaded_core.executable_path.relative_to(resolved_server.path)
    )
    config.save()
    return resolved_server, True


def change_server_image(
    config: UserConfig,
    server: ManagedServer,
    image: str,
) -> ManagedServer:
    resolved_server = _ensure_server_can_modify_image(config, server)

    from luminesk.utils.docker import validate_runtime_image

    try:
        resolved_server.runtime_image = validate_runtime_image(image)
    except ValueError as exc:
        raise ServerManagerError(str(exc)) from exc

    config.save()
    return resolved_server


def delete_server(
    config: UserConfig,
    tag: str | None = None,
    directory: Path | None = None,
) -> ManagedServer:
    resolved_server = resolve_server(config=config, tag=tag, directory=directory)
    runtime_view = get_runtime_view(config, resolved_server)

    if runtime_view.status == "running" or runtime_view.loop_enabled:
        raise ServerManagerError(
            t("manager.server_must_be_stopped_for_delete", tag=resolved_server.tag)
        )

    metadata_dir = resolved_server.path / ".luminesk"

    if metadata_dir.is_dir():
        try:
            import shutil
            shutil.rmtree(metadata_dir)
        except Exception as exc:
            raise ServerManagerError(
                t("manager.delete_metadata_failed", directory=metadata_dir, error=exc)
            )

    deleted_server = config.unregister_server(resolved_server.tag)
    config.save()
    return deleted_server


def is_server_setup_completed(server: ManagedServer, core: BaseCore) -> bool:
    if getattr(core, "dont_create_config", False):
        return True

    config_path = server.path / core.config_file

    if not config_path.exists():
        return False

    try:
        content = config_path.read_text(encoding="utf-8").strip()
        header = t("manager.server_config_header").strip()
        if not content or content == header:
            return False
    except OSError:
        return False

    return True


def run_server(
    config: UserConfig,
    server: ManagedServer,
    loop: bool = False,
    detached: bool = False,
    console: Console | None = None,
) -> int:
    sync_runtime_states(config)
    runtime_view = _build_runtime_view(config, server)

    if runtime_view.status == "running":
        raise ServerManagerError(
            t("manager.server_already_running", tag=server.tag, pid=runtime_view.pid)
        )

    if not server.executable_path.is_file():
        raise ServerManagerError(
            t("manager.executable_not_found", executable_path=server.executable_path)
        )

    from luminesk.core.registry import registry

    core = registry.get_by_id(server.core_id)

    if core is not None and core.required_setup:
        if detached and not is_server_setup_completed(server, core):
            if console is not None:
                console.print(
                    ansi_text(
                        warning(
                            t(
                                "cli.start.setup_warning",
                                core_name=core.name,
                                tag=server.tag,
                            )
                        )
                    )
                )

    try:
        launch_result = launcher.launch_server_detached(
            server,
            loop=loop,
            config=config,
            console=console,
        )
    except RuntimeError as exc:
        raise ServerManagerError(str(exc)) from exc

    if console is not None:
        launch_details = [
            success(t("manager.docker_started"), bold=True),
            format_kv(
                t("label.server"),
                format_server(server.name, server.tag),
                value_color=None,
            ),
            format_kv(t("label.container"), launch_result.container_name),
            format_kv(t("label.image"), launch_result.runtime_image),
            format_kv(t("label.memory_limit"), launch_result.memory_limit),
            format_kv(t("label.log"), launch_result.log_path, dim_value=True),
        ]
        console.print(success_panel("\n".join(launch_details)))

    if detached:
        if console is not None:
            attach_command = accent(f"nesk attach {server.tag}", bold=True)
            console.print(
                info_panel(
                    attach_command,
                    title=t("cli.start.detached_attach_title"),
                )
            )
        return 0

    return launcher.follow_container_logs(
        launch_result.container_name,
        config=config,
        server_tag=server.tag,
    )


def attach_server(
    config: UserConfig,
    server: ManagedServer,
) -> int:
    sync_runtime_states(config)
    runtime_view = _build_runtime_view(config, server)

    if runtime_view.status != "running" or runtime_view.docker_container_name is None:
        raise ServerManagerError(t("manager.server_not_running", tag=server.tag))

    return launcher.follow_container_logs(
        runtime_view.docker_container_name,
        config=config,
        server_tag=server.tag,
    )


def format_timedelta(value: timedelta | None) -> str:
    if value is None:
        return "-"

    total_seconds = int(value.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _ensure_registration_target_available(
    config: UserConfig,
    tag: str,
    directory: Path,
) -> None:
    if config.get_server_by_tag(tag) is not None:
        raise ServerManagerError(t("manager.tag_in_use", tag=tag))

    for registered_server in config.get_servers():
        if registered_server.path == directory:
            raise ServerManagerError(
                t(
                    "manager.directory_already_registered",
                    directory=directory,
                    tag=registered_server.tag,
                )
            )


def _ensure_server_can_modify_core(
    config: UserConfig,
    server: ManagedServer,
) -> ManagedServer:
    sync_runtime_states(config)
    resolved_server = config.get_server_by_tag(server.tag) or server
    runtime_view = _build_runtime_view(config, resolved_server)

    if runtime_view.status == "running" or runtime_view.loop_enabled:
        raise ServerManagerError(
            t(
                "manager.server_must_be_stopped_for_core_change",
                tag=resolved_server.tag,
            )
        )

    return resolved_server


def _ensure_server_can_modify_image(
    config: UserConfig,
    server: ManagedServer,
) -> ManagedServer:
    sync_runtime_states(config)
    resolved_server = config.get_server_by_tag(server.tag) or server
    runtime_view = _build_runtime_view(config, resolved_server)

    if runtime_view.status == "running" or runtime_view.loop_enabled:
        raise ServerManagerError(
            t(
                "manager.server_must_be_stopped_for_image_change",
                tag=resolved_server.tag,
            )
        )

    return resolved_server


def _remove_previous_managed_executable(
    server: ManagedServer, new_executable_path: Path
) -> None:
    previous_executable_path = server.executable_path

    if (
        server.core_hash is not None
        and previous_executable_path != new_executable_path
        and previous_executable_path.exists()
    ):
        previous_executable_path.unlink()


def _find_server_by_pid(config: UserConfig, pid: int) -> ManagedServer | None:
    for server in config.get_servers():
        if server.runtime.pid == pid:
            return server

    return None


def _get_active_docker_container_name(server: ManagedServer) -> str | None:
    container_name = server.runtime.docker_container_name

    if container_name is None:
        return None

    if docker_container_is_running(container_name):
        return container_name

    return None


def _is_server_runtime_alive(server: ManagedServer) -> bool:
    container_name = server.runtime.docker_container_name

    if container_name is not None:
        return docker_container_is_running(container_name)

    return _is_process_alive(server.runtime.pid)


def _sync_docker_runtime_pid(server: ManagedServer) -> bool:
    container_name = server.runtime.docker_container_name

    if container_name is None:
        return False

    pid = get_docker_container_pid(container_name)

    if pid is not None and pid != server.runtime.pid:
        server.runtime.pid = pid
        return True

    return False


def _get_runtime_exit_code(server: ManagedServer) -> int | None:
    container_name = server.runtime.docker_container_name

    if container_name is None:
        return server.runtime.last_exit_code

    return get_docker_container_exit_code(container_name)


def _cleanup_stopped_docker_runtime(server: ManagedServer) -> None:
    container_name = server.runtime.docker_container_name

    if container_name is not None:
        remove_docker_container(container_name)


def _stop_docker_server_gracefully(
    container_name: str,
    *,
    force: bool,
    timeout_seconds: float = 20.0,
) -> None:
    if force:
        stop_docker_container(container_name)
        return

    try:
        send_docker_ctrl_c(container_name)
    except RuntimeError:
        stop_docker_container(container_name)
        return

    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if not docker_container_is_running(container_name):
            return
        time.sleep(0.25)

    stop_docker_container(container_name)


def _get_parent_pid(pid: int | None) -> int | None:
    if pid is None:
        return None

    proc_status_path = Path(f"/proc/{pid}/status")

    try:
        if proc_status_path.is_file():
            for line in proc_status_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("PPid:"):
                    return int(line.split(":", 1)[1].strip())
    except (OSError, ValueError):
        pass

    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def _is_kill_signal(sig: int) -> bool:
    return sig == KILL_SIGNAL or _get_signal_name(sig) == "SIGKILL"


def _get_signal_name(sig: int) -> str:
    if sig == KILL_SIGNAL:
        return "SIGKILL"

    if sig == STOP_SIGNAL:
        return "SIGINT"

    try:
        return signal.Signals(sig).name
    except ValueError:
        return f"signal {sig}"


def _restore_cached_core(
    core: CoreProvider,
    download_info: CoreDownloadInfo,
    target_directory: Path,
    expected_hash: str | None,
    console: Console | None = None,
) -> DownloadedCore | None:
    cache_paths = _get_cached_core_paths(core, download_info)

    if not cache_paths.executable_path.is_file():
        return None

    file_name = _read_cached_file_name(cache_paths.metadata_path)

    if file_name is None:
        return None

    cached_hash = _read_cached_hash(cache_paths.metadata_path)
    target_hash = expected_hash if expected_hash is not None else cached_hash

    if target_hash is None:
        return None

    if cached_hash is None or not hmac.compare_digest(cached_hash.lower(), target_hash.lower()):
        return None

    if not _file_hash_matches(cache_paths.executable_path, target_hash):
        return None

    target_path = _resolve_download_target_path(target_directory, file_name)

    try:
        _copy_cached_executable(cache_paths.executable_path, target_path)
    except OSError:
        return None

    if console is not None:
        message = t(
            "manager.using_cached_core",
            core_name=accent(core.name, bold=True),
            hash=muted(download_info.hash[:12]),
        )
        console.print(ansi_text(message))

    return DownloadedCore(executable_path=target_path, hash=download_info.hash)


def _store_core_in_cache(
    core: CoreProvider,
    download_info: CoreDownloadInfo,
    source_path: Path,
    hash_val: str,
) -> None:
    cache_paths = _get_cached_core_paths(core, download_info)
    temp_cache_path = _get_temporary_file_path(cache_paths.executable_path)
    temp_metadata_path = _get_temporary_file_path(cache_paths.metadata_path)

    try:
        cache_paths.cache_directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, temp_cache_path)
        temp_cache_path.replace(cache_paths.executable_path)
        temp_metadata_path.write_text(
            json.dumps(
                {
                    "file_name": source_path.name,
                    "hash": hash_val,
                    "source_url": download_info.url,
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp_metadata_path.replace(cache_paths.metadata_path)
    except OSError:
        _cleanup_path(temp_cache_path)
        _cleanup_path(temp_metadata_path)


def _get_cached_core_paths(
    core: CoreProvider,
    download_info: CoreDownloadInfo,
) -> CachedCorePaths:
    hash_key = _sanitize_cache_component(download_info.hash)
    url_hash = hashlib.sha256(download_info.url.encode("utf-8")).hexdigest()[:12]
    cache_key = f"{hash_key[:12]}-{url_hash}"
    cache_directory = CORE_CACHE_DIR / core.id

    suffix = ""

    if isinstance(core, GitHubRelease) and core.release_file:
        suffix = Path(core.release_file).suffix
    elif hasattr(core, "classifier") and getattr(core, "classifier"):
        suffix = ".jar"
    else:
        suffix = ".jar"

    return CachedCorePaths(
        cache_directory=cache_directory,
        executable_path=cache_directory / f"{cache_key}{suffix}",
        metadata_path=cache_directory / f"{cache_key}.json",
    )


def _sanitize_cache_component(value: str) -> str:
    sanitized_value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return sanitized_value.strip(".-") or "latest"


def _read_cached_file_name(metadata_path: Path) -> str | None:
    payload = _read_cached_metadata(metadata_path)

    if not isinstance(payload, dict):
        return None

    file_name = payload.get("file_name")

    if not isinstance(file_name, str):
        return None

    normalized_file_name = Path(file_name).name

    if normalized_file_name != file_name or not _is_safe_download_file_name(
        normalized_file_name
    ):
        return None

    return normalized_file_name


def _read_cached_hash(metadata_path: Path) -> str | None:
    payload = _read_cached_metadata(metadata_path)

    if not isinstance(payload, dict):
        return None

    hash_val = payload.get("hash") or payload.get("sha256")

    if not isinstance(hash_val, str):
        return None

    normalized_hash = hash_val.strip().lower()

    if len(normalized_hash) in {40, 64} and re.fullmatch(r"[a-fA-F0-9]+", normalized_hash):
        return normalized_hash

    return None


def _read_cached_metadata(metadata_path: Path) -> dict[str, object] | None:
    if not metadata_path.is_file():
        return None

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _file_hash_matches(path: Path, expected_hash: str) -> bool:
    if len(expected_hash) == 40:
        hash_obj = hashlib.sha1()
    else:
        hash_obj = hashlib.sha256()

    try:
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hash_obj.update(chunk)
    except OSError:
        return False

    return hmac.compare_digest(hash_obj.hexdigest().lower(), expected_hash.lower())


def _copy_cached_executable(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_target_path = _get_temporary_file_path(target_path)
    _cleanup_path(temp_target_path)
    shutil.copy2(source_path, temp_target_path)
    temp_target_path.replace(target_path)


def _get_temporary_file_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.part")


def _cleanup_path(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _resolve_download_file_name(
    response: httpx.Response,
    download_url: str,
    core: CoreProvider,
) -> str:
    content_disposition = response.headers.get("content-disposition")

    if content_disposition:
        file_name = _extract_file_name_from_content_disposition(content_disposition)
        if file_name:
            return _require_safe_download_file_name(file_name)

    response_url = str(response.url)
    parsed_url = urlparse(response_url or download_url)
    file_name = Path(unquote(parsed_url.path)).name

    if _is_safe_download_file_name(file_name):
        return file_name

    suffix = ""

    if isinstance(core, GitHubRelease) and core.release_file:
        suffix = Path(core.release_file).suffix
    elif hasattr(core, "classifier") and getattr(core, "classifier"):
        suffix = ".jar"
    else:
        suffix = ".jar"

    return f"{core.id}{suffix}"


def _extract_file_name_from_content_disposition(header_value: str) -> str | None:
    utf8_match = re.search(
        r"filename\*=UTF-8''([^;]+)", header_value, flags=re.IGNORECASE
    )

    if utf8_match:
        return unquote(utf8_match.group(1).strip().strip('"'))

    plain_match = re.search(r'filename="?([^";]+)"?', header_value, flags=re.IGNORECASE)

    if plain_match:
        return plain_match.group(1).strip()

    return None


def _parse_content_length(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None

    try:
        content_length = int(raw_value)
    except ValueError:
        return None

    return content_length if content_length >= 0 else None


def _resolve_download_target_path(target_directory: Path, file_name: str) -> Path:
    root = target_directory.expanduser().resolve()
    target_path = (root / _require_safe_download_file_name(file_name)).resolve()

    try:
        target_path.relative_to(root)
    except ValueError as exc:
        raise ServerManagerError(
            t("manager.download_target_escape", target_path=target_path)
        ) from exc

    return target_path


def _require_safe_download_file_name(file_name: str) -> str:
    decoded_file_name = unquote(file_name).strip()

    if not _is_safe_download_file_name(decoded_file_name):
        raise ServerManagerError(
            t("manager.unsafe_download_filename", file_name=repr(file_name))
        )

    return decoded_file_name


def _is_safe_download_file_name(file_name: str) -> bool:
    if not file_name or file_name in {".", ".."}:
        return False

    if "/" in file_name or "\\" in file_name:
        return False

    path = Path(file_name)

    if path.is_absolute() or path.name != file_name:
        return False

    return path.suffix.lower() in {".jar", ".phar", ".exe", ""}


def _validate_download_size(size: int | None) -> None:
    if size is None:
        return

    if size > MAX_CORE_DOWNLOAD_BYTES:
        max_mib = MAX_CORE_DOWNLOAD_BYTES // (1024 * 1024)
        raise ServerManagerError(t("manager.download_too_large", max_mib=max_mib))





def _is_process_alive(pid: int | None) -> bool:
    if pid is None:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False

    return True


def _send_signal(pid: int | None, sig: int) -> None:
    if pid is None:
        raise ServerManagerError(t("manager.pid_undefined"))

    try:
        os.kill(pid, sig)
    except ProcessLookupError as exc:
        raise ServerManagerError(t("manager.process_missing", pid=pid)) from exc
    except PermissionError as exc:
        raise ServerManagerError(
            t("manager.signal_permission_denied", pid=pid)
        ) from exc


def _get_uptime(server: ManagedServer) -> timedelta | None:
    if server.runtime.last_started_at is None:
        return None

    return utc_now() - server.runtime.last_started_at
