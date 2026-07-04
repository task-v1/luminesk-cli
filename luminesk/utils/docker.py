from __future__ import annotations

import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from luminesk.core.messages import t
from luminesk.utils.config_parser import get_server_port

DEFAULT_FALLBACK_IMAGE = "eclipse-temurin:21-jre"
DEFAULT_DOCKER_MEMORY_LIMIT = "1g"
DOCKER_SERVER_DIR = "/server"
MEMORY_LIMIT_RE = re.compile(r"^[1-9][0-9]*(?:[bkmg])?$", re.IGNORECASE)


def get_docker_entrypoint_script(console_pipe: str) -> str:
    return f"""
mkdir -p .luminesk/logs
rm -f {console_pipe}
mkfifo {console_pipe}
chmod 600 {console_pipe}
trap 'rm -f {console_pipe} /tmp/luminesk-exit' EXIT

while true; do
	exec 3<> {console_pipe}
	(eval "$LUMINESK_RUN_COMMAND" < {console_pipe}; echo $? > /tmp/luminesk-exit) 2>&1 | tee -a "$LUMINESK_LOG_PATH"
	exit_code=$(cat /tmp/luminesk-exit 2>/dev/null || echo 0)
	exec 3>&-

	if [ "${{LUMINESK_LOOP:-0}}" != "1" ]; then
		exit "$exit_code"
	fi

	printf '[Luminesk] Server exited with code %s. Restarting in %s seconds.\\n' "$exit_code" "${{LUMINESK_RESTART_DELAY:-5}}" | tee -a "$LUMINESK_LOG_PATH"
	sleep "${{LUMINESK_RESTART_DELAY:-5}}"
done
""".strip()


class DockerLaunchTarget(Protocol):
    tag: str
    path: Path
    executable_name: str
    core_id: str
    config_file: str
    port_way: str


def normalize_memory_limit(memory_limit: str | None) -> str:
    normalized = (
        DEFAULT_DOCKER_MEMORY_LIMIT
        if memory_limit is None
        else memory_limit.strip().lower()
    )

    if not MEMORY_LIMIT_RE.fullmatch(normalized):
        raise ValueError(
            t(
                "docker.invalid_memory_limit",
                memory_limit=memory_limit or "",
            )
        )

    return normalized


def normalize_runtime_image(image: str | None) -> str:
    normalized = "latest" if image is None else image.strip()

    if not normalized:
        raise ValueError(t("docker.invalid_runtime_image", image=image or ""))

    if any(char.isspace() for char in normalized):
        raise ValueError(t("docker.invalid_runtime_image", image=image or ""))

    return normalized


def get_docker_binary() -> str:
    docker_bin = shutil.which("docker")

    if docker_bin is None:
        raise RuntimeError(t("docker.not_found"))

    return docker_bin


def build_docker_container_name(tag: str) -> str:
    sanitized = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in tag.strip().lower()
    ).strip("-_")
    return f"luminesk-{sanitized or 'server'}"


def build_docker_logs_command(container_name: str) -> tuple[str, ...]:
    return ("docker", "logs", "--follow", container_name)


def build_docker_run_command(
    server: DockerLaunchTarget,
    log_path: Path,
    *,
    container_name: str | None = None,
    image: str = DEFAULT_FALLBACK_IMAGE,
    loop: bool = False,
    memory_limit: str | None = None,
    restart_delay_seconds: int = 5,
) -> tuple[str, ...]:
    normalized_memory_limit = normalize_memory_limit(memory_limit)
    resolved_container_name = container_name or build_docker_container_name(server.tag)
    mount_source = _format_mount_source(server.path)
    console_pipe = f"/tmp/luminesk-console-{resolved_container_name}.pipe"
    entrypoint_script = get_docker_entrypoint_script(console_pipe)

    # Resolve core run command dynamically from registry
    from luminesk.core.registry import registry

    core_id = getattr(server, "core_id", None)
    core = registry.get_by_id(core_id) if core_id else None

    if core is not None:
        run_command = core.get_run_command(server.executable_name)
    else:
        if server.executable_name.endswith(".jar"):
            run_command = f"java -jar {server.executable_name}"
        elif server.executable_name.endswith(".phar"):
            run_command = f"php {server.executable_name}"
        else:
            run_command = f"./{server.executable_name}"

    return (
        "docker",
        "run",
        "--detach",
        "--interactive",
        "--name",
        resolved_container_name,
        "--memory",
        normalized_memory_limit,
        *_network_args(server),
        "--workdir",
        DOCKER_SERVER_DIR,
        "--volume",
        f"{mount_source}:{DOCKER_SERVER_DIR}",
        "--env",
        f"LUMINESK_RUN_COMMAND={run_command}",
        "--env",
        f"LUMINESK_LOG_PATH={_to_container_path(log_path)}",
        "--env",
        f"LUMINESK_LOOP={'1' if loop else '0'}",
        "--env",
        f"LUMINESK_RESTART_DELAY={restart_delay_seconds}",
        image,
        "sh",
        "-c",
        entrypoint_script,
    )


def docker_container_is_running(container_name: str) -> bool:
    try:
        result = _run_docker(
            ("inspect", "--format", "{{.State.Running}}", container_name),
            check=False,
        )
    except RuntimeError:
        return False

    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def get_docker_container_pid(container_name: str) -> int | None:
    try:
        result = _run_docker(
            ("inspect", "--format", "{{.State.Pid}}", container_name),
            check=False,
        )
    except RuntimeError:
        return None

    if result.returncode != 0:
        return None

    try:
        pid = int(result.stdout.strip())
    except ValueError:
        return None

    return pid if pid > 0 else None


def get_docker_container_exit_code(container_name: str) -> int | None:
    try:
        result = _run_docker(
            ("inspect", "--format", "{{.State.ExitCode}}", container_name),
            check=False,
        )
    except RuntimeError:
        return None

    if result.returncode != 0:
        return None

    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def remove_docker_container(container_name: str) -> None:
    try:
        _run_docker(("rm", "--force", container_name), check=False)
    except RuntimeError:
        return


def stop_docker_container(container_name: str, timeout_seconds: int = 10) -> None:
    result = _run_docker(
        ("stop", "--time", str(timeout_seconds), container_name),
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or t("docker.stop_failed"))


def kill_docker_container(container_name: str) -> None:
    result = _run_docker(("kill", container_name), check=False)

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or t("docker.kill_failed"))


def send_docker_command(container_name: str, command: str) -> None:
    console_pipe = f"/tmp/luminesk-console-{container_name}.pipe"

    try:
        result = _run_docker(
            (
                "exec",
                container_name,
                "sh",
                "-c",
                f'printf "%s\\n" "$1" > {console_pipe}',
                "luminesk-send",
                command,
            ),
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(t("docker.send_command_timeout")) from exc

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or t("docker.send_command_failed"))


def send_docker_ctrl_c(container_name: str) -> None:
    cmd = (
        'pids=$(pgrep -f "java|php|phar|pocketmine|dragonfly|pumpkin|endstone" 2>/dev/null || '
        'pidof java php 2>/dev/null || '
        'ps -ef | grep -E "java|php|phar|pocketmine|dragonfly|pumpkin|endstone" | grep -v grep | awk "{print \\$2}" 2>/dev/null || '
        'ps | grep -E "java|php|phar|pocketmine|dragonfly|pumpkin|endstone" | grep -v grep | awk "{print \\$1}" 2>/dev/null || '
        'for p in /proc/[0-9]*; do '
        '[ -d "$p" ] || continue; '
        'pid=${p##*/}; [ "$pid" = "1" ] && continue; '
        'name=$(cat "$p/comm" "$p/cmdline" 2>/dev/null); '
        'case "$name" in *java*|*php*|*phar*|*pocketmine*|*dragonfly*|*pumpkin*|*endstone*) echo "$pid";; esac; '
        'done); '
        'if [ -n "$pids" ]; then kill -2 $pids; fi'
    )

    try:
        result = _run_docker(
            (
                "exec",
                container_name,
                "sh",
                "-c",
                cmd,
            ),
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(t("docker.send_command_timeout")) from exc

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or t("docker.send_command_failed"))


def _run_docker(
    args: tuple[str, ...],
    *,
    check: bool,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    docker_bin = get_docker_binary()
    return subprocess.run(
        [docker_bin, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
        timeout=timeout,
    )


def _to_container_path(path: Path) -> str:
    name = path.name
    return f"{DOCKER_SERVER_DIR}/.luminesk/logs/{name}"


def _format_mount_source(path: Path) -> str:
    return str(path.expanduser().resolve()).replace("\\", "/")


def _network_args(server: DockerLaunchTarget) -> tuple[str, ...]:
    if platform.system().lower() == "linux":
        return ("--network", "host")

    config_file = getattr(server, "config_file", "server.properties")
    port_way = getattr(server, "port_way", "server-port")
    port = get_server_port(server.path, config_file, port_way)

    return (
        "--publish",
        f"{port}:{port}/udp",
        "--publish",
        f"{port}:{port}/tcp",
    )


def docker_image_exists(image: str) -> bool:
    # 1. Check if the image exists in a registry
    try:
        result = _run_docker(("manifest", "inspect", image), check=False, timeout=10)
        if result.returncode == 0:
            return True
    except Exception:
        pass

    # 2. Check if the image exists locally
    try:
        result = _run_docker(("image", "inspect", image), check=False, timeout=5)
        if result.returncode == 0:
            return True
    except Exception:
        pass

    return False


def validate_runtime_image(image: str | None) -> str:
    normalized = normalize_runtime_image(image)

    # Reject version-only tags (starts with a digit, and contains no ":" or "/")
    if "/" not in normalized and ":" not in normalized and (normalized[0].isdigit() if normalized else False):
        raise ValueError(t("docker.version_only_rejected", image=normalized))

    # Perform existence check
    if not docker_image_exists(normalized):
        raise ValueError(t("docker.image_not_found", image=normalized))

    return normalized
