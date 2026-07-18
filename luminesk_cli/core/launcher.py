from __future__ import annotations

import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console

from luminesk_cli.core.config import UserConfig
from luminesk_cli.core.messages import t
from luminesk_cli.models.launcher import DetachedLaunchResult, ServerLaunchTarget
from luminesk_cli.utils.docker import (
    DEFAULT_FALLBACK_IMAGE,
    build_docker_container_name,
    build_docker_logs_command,
    build_docker_run_command,
    docker_container_is_running,
    get_docker_binary,
    get_docker_container_exit_code,
    get_docker_container_pid,
    normalize_memory_limit,
    remove_docker_container,
    send_docker_command,
    send_docker_ctrl_c,
    stop_docker_container,
)
from luminesk_cli.utils.rich_utils import accent, ansi_text, warning


def build_log_path(server: ServerLaunchTarget, now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")
    return server.path / ".luminesk_cli" / "logs" / f"{server.tag}-{timestamp}.log"


def launch_server_detached(
    server: ServerLaunchTarget,
    loop: bool = False,
    *,
    memory_limit: str | None = None,
    image: str | None = None,
    config: UserConfig | None = None,
    console: Console | None = None,
) -> DetachedLaunchResult:
    docker_bin = get_docker_binary()
    from luminesk_cli.core.registry import registry

    core = registry.get_by_id(getattr(server, "core_id", ""))

    if image:
        resolved_image = image
    elif (
        getattr(server, "runtime_image", None)
        and server.runtime_image != DEFAULT_FALLBACK_IMAGE
    ):
        resolved_image = (
            core.resolve_image(server.runtime_image)
            if core is not None
            else server.runtime_image
        )
    elif core is not None:
        resolved_image = core.get_docker_image()
    else:
        resolved_image = DEFAULT_FALLBACK_IMAGE

    ensure_docker_image(resolved_image, docker_bin=docker_bin, console=console)
    normalized_memory_limit = normalize_memory_limit(
        memory_limit or server.memory_limit
    )
    log_path = build_log_path(server)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    container_name = build_docker_container_name(server.tag)

    if docker_container_is_running(container_name):
        raise RuntimeError(
            t("launcher.docker_container_exists", container_name=container_name)
        )

    remove_docker_container(container_name)

    command = build_docker_run_command(
        server,
        log_path,
        container_name=container_name,
        image=resolved_image,
        loop=loop,
        memory_limit=normalized_memory_limit,
    )
    attach_command = build_docker_logs_command(container_name)

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"[{datetime.now().astimezone().isoformat()}] Launching Docker container {container_name}: "
            f"{' '.join(command)}\n"
        )
        result = subprocess.run(
            [docker_bin, *command[1:]],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.stderr:
            log_file.write(result.stderr)
        if result.returncode != 0:
            error = result.stderr.strip() or f"exit code {result.returncode}"
            raise RuntimeError(
                t(
                    "launcher.docker_run_failed",
                    exit_code=result.returncode,
                    error=error,
                )
            )

    container_id = result.stdout.strip()
    pid = get_docker_container_pid(container_name)
    loaded_config = config or UserConfig.load()
    registered_server = loaded_config.get_server_by_tag(server.tag)

    if registered_server is not None:
        registered_server.memory_limit = normalized_memory_limit

    loaded_config.mark_server_started(
        server.tag,
        pid=pid,
        loop_enabled=loop,
        docker_container_id=container_id,
        docker_container_name=container_name,
        docker_memory_limit=normalized_memory_limit,
    )
    loaded_config.save()

    return DetachedLaunchResult(
        container_id=container_id,
        container_name=container_name,
        command=command,
        attach_command=attach_command,
        log_path=log_path,
        memory_limit=normalized_memory_limit,
        runtime_image=resolved_image,
    )


def follow_container_logs(
    container_name: str,
    *,
    config: UserConfig,
    server_tag: str,
) -> int:
    docker_bin = get_docker_binary()
    process = subprocess.Popen(
        [docker_bin, "logs", "--follow", container_name],
        stdin=subprocess.DEVNULL,
    )
    _start_console_forwarder(container_name, process)

    try:
        logs_exit_code = process.wait()
    except KeyboardInterrupt:
        console = Console()
        with console.status(ansi_text(warning(t("launcher.stopping_server"))), spinner="dots"):
            try:
                send_docker_ctrl_c(container_name)
            except RuntimeError:
                pass

            server = config.get_server_by_tag(server_tag)
            loop_enabled = server.runtime.loop_enabled if server is not None else False

            if loop_enabled:
                deadline = time.monotonic() + 5.0

                while time.monotonic() < deadline:
                    if not docker_container_is_running(container_name):
                        break

                    time.sleep(0.25)
                else:
                    try:
                        stop_docker_container(container_name)
                    except Exception:
                        pass
            else:
                deadline = time.monotonic() + 20.0

                while time.monotonic() < deadline:
                    if not docker_container_is_running(container_name):
                        break

                    time.sleep(0.25)
                else:
                    try:
                        stop_docker_container(container_name)
                    except Exception:
                        pass

            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        logs_exit_code = 130

    if docker_container_is_running(container_name):
        return logs_exit_code

    exit_code = get_docker_container_exit_code(container_name)
    remove_docker_container(container_name)
    config.mark_server_stopped(server_tag, exit_code=exit_code)
    config.save()
    return exit_code if exit_code is not None else logs_exit_code


def _start_console_forwarder(
    container_name: str,
    process: subprocess.Popen,
) -> threading.Thread | None:
    if not sys.stdin.isatty():
        return None

    def _forward() -> None:
        try:
            for line in sys.stdin:
                command = line.rstrip("\n")

                try:
                    send_docker_command(container_name, command)
                except RuntimeError:
                    if not docker_container_is_running(container_name):
                        break
                    continue

            if docker_container_is_running(container_name):
                console = Console()
                console.print(ansi_text(warning(t("launcher.detaching_server"))))
                process.terminate()
        except Exception:
            pass

    thread = threading.Thread(
        target=_forward, name=f"luminesk_cli-console-{container_name}"
    )
    thread.daemon = True
    thread.start()
    return thread


def ensure_docker_image(
    image: str,
    *,
    docker_bin: str | None = None,
    console: Console | None = None,
) -> None:
    resolved_docker_bin = docker_bin or get_docker_binary()
    inspect_result = subprocess.run(
        [resolved_docker_bin, "image", "inspect", image],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if inspect_result.returncode == 0:
        return

    if console is None:
        pull_result = subprocess.run(
            [resolved_docker_bin, "pull", image],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if pull_result.returncode != 0:
            error = pull_result.stderr.strip() or pull_result.stdout.strip()
            raise RuntimeError(
                t("launcher.docker_pull_failed", image=image, error=error)
            )
    else:
        status_message = ansi_text(
            t(
                "launcher.docker_pull_start",
                image=accent(image, bold=True),
            )
        )
        with console.status(status_message, spinner="dots") as status:
            process = subprocess.Popen(
                [resolved_docker_bin, "pull", image],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if process.stdout is not None:
                for line in process.stdout:
                    cleaned_line = line.strip()

                    if cleaned_line:
                        if len(cleaned_line) > 60:
                            cleaned_line = cleaned_line[:57] + "..."

                        status.update(f"{status_message} ({cleaned_line})")
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(
                    t(
                        "launcher.docker_pull_failed",
                        image=image,
                        error=f"exit code {return_code}",
                    )
                )
