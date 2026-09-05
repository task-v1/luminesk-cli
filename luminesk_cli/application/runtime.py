"""Manifest-driven single-server Docker runtime with argv-only execution."""

from __future__ import annotations

import re
import socket
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from luminesk_cli.domain.errors import RuntimeOperationError, ValidationError
from luminesk_cli.domain.instance import InstanceState, RuntimeState
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, Lockfile, load_lockfile
from luminesk_cli.domain.manifest import Check, Manifest, RuntimePort, load_manifest
from luminesk_cli.infrastructure.recipe_snapshot import load_verified_installed_recipe
from luminesk_cli.infrastructure.state import load_state, write_state

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
MEMORY_RE = re.compile(r"^[1-9][0-9]*(?:[bkmg])?$", re.IGNORECASE)
CONTAINER_NAME_RE = re.compile(r"[^a-z0-9_.-]+")


class DockerRuntime:
    def __init__(self, runner: CommandRunner = subprocess.run) -> None:
        self._runner = runner

    def start(
        self,
        root: Path,
        *,
        input_overrides: Mapping[str, str | int | bool] | None = None,
        wait_for_readiness: bool = True,
    ) -> InstanceState:
        root = root.resolve()
        state, manifest, lockfile = _load_instance(root)

        if state.pending_transaction is not None:
            raise RuntimeOperationError("cannot start during a pending transaction")

        if state.applied_lock_digest != lockfile.digest:
            raise ValidationError("instance state does not match lockfile")

        if state.runtime.status == "running" and state.runtime.container_id:
            if self.is_running(state.runtime.container_id):
                return state

        values = {**state.inputs, **(input_overrides or {})}
        container_name = _container_name(state)
        self._run(["docker", "rm", "--force", container_name], check=False)
        command = build_run_argv(
            root,
            manifest,
            lockfile.runtime.image,
            container_name,
            values,
        )
        result = self._run(command, check=False)

        if result.returncode != 0:
            raise RuntimeOperationError(
                "Docker failed to start the instance",
                stderr=result.stderr[-4000:],
                exit_code=result.returncode,
            )

        container_id = result.stdout.strip()

        if not container_id:
            raise RuntimeOperationError("Docker returned an empty container id")

        running_state = replace(
            state,
            runtime=RuntimeState(
                driver="docker",
                container_id=container_id,
                status="running",
            ),
            updated_at=datetime.now(UTC).isoformat(),
        )
        write_state(root, running_state)

        try:
            readiness_at = None

            if wait_for_readiness:
                self.wait_ready(root, manifest, running_state, values)
                readiness_at = datetime.now(UTC).isoformat()

            committed = replace(
                running_state,
                last_readiness_at=readiness_at,
                updated_at=datetime.now(UTC).isoformat(),
            )
            write_state(root, committed)
            return committed
        except BaseException:
            self.stop(root, remove=True)
            raise

    def stop(self, root: Path, *, remove: bool = False) -> InstanceState:
        root = root.resolve()
        state, manifest, _ = _load_instance(root)
        identifier = state.runtime.container_id or _container_name(state)
        result = self._run(
            [
                "docker",
                "stop",
                "--time",
                str(manifest.runtime.stop_timeout),
                identifier,
            ],
            check=False,
        )

        if result.returncode != 0 and self.is_running(identifier):
            raise RuntimeOperationError(
                "Docker failed to stop the instance", stderr=result.stderr[-4000:]
            )

        if remove:
            self._run(["docker", "rm", "--force", identifier], check=False)

        stopped = replace(
            state,
            runtime=RuntimeState(driver="docker", status="stopped"),
            updated_at=datetime.now(UTC).isoformat(),
        )
        write_state(root, stopped)
        return stopped

    def status(self, root: Path) -> InstanceState:
        root = root.resolve()
        state, _, _ = _load_instance(root)
        identifier = state.runtime.container_id
        running = bool(identifier and self.is_running(identifier))
        actual_status: Literal["running", "stopped"] = (
            "running" if running else "stopped"
        )

        if state.runtime.status == actual_status:
            return state

        updated = replace(
            state,
            runtime=RuntimeState(
                driver="docker",
                container_id=identifier if running else None,
                status=actual_status,
            ),
            updated_at=datetime.now(UTC).isoformat(),
        )
        write_state(root, updated)
        return updated

    def logs(self, root: Path, *, follow: bool = False) -> int | str:
        state, _, _ = _load_instance(root.resolve())
        identifier = state.runtime.container_id or _container_name(state)

        if follow:
            try:
                follow_result = self._runner(
                    ["docker", "logs", "--follow", identifier],
                    check=False,
                    shell=False,
                )
            except OSError as exc:
                raise RuntimeOperationError(
                    f"cannot follow Docker logs: {exc}"
                ) from exc
            if follow_result.returncode != 0:
                raise RuntimeOperationError(
                    "cannot follow Docker logs",
                    exitCode=follow_result.returncode,
                )
            return 0

        result = self._run(["docker", "logs", identifier], check=False)

        if result.returncode != 0:
            raise RuntimeOperationError(
                "cannot read Docker logs", stderr=result.stderr[-4000:]
            )

        return result.stdout

    def attach(self, root: Path) -> int:
        state, _, _ = _load_instance(root.resolve())
        identifier = state.runtime.container_id or _container_name(state)
        try:
            result = self._runner(
                ["docker", "attach", "--sig-proxy=true", identifier],
                check=False,
                shell=False,
            )
        except OSError as exc:
            raise RuntimeOperationError(f"cannot attach to Docker: {exc}") from exc
        if result.returncode != 0:
            raise RuntimeOperationError(
                "Docker attach failed",
                exitCode=result.returncode,
            )
        return 0

    def is_running(self, identifier: str) -> bool:
        result = self._run(
            ["docker", "inspect", "--format", "{{.State.Running}}", identifier],
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip().lower() == "true"

    def wait_ready(
        self,
        root: Path,
        manifest: Manifest,
        state: InstanceState,
        values: Mapping[str, str | int | bool],
    ) -> None:
        checks = [check for check in manifest.checks if check.phase == "readiness"]

        if not checks:
            checks = [
                Check(
                    id="process-alive",
                    phase="readiness",
                    kind="process-alive",
                    timeout=5,
                )
            ]

        for check in checks:
            self._wait_check(root, state, check, values)

    def check_readiness(self, root: Path) -> InstanceState:
        """Run the declared readiness policy against the live instance."""

        root = root.resolve()
        state, manifest, _ = _load_instance(root)

        if state.runtime.status != "running" or not state.runtime.container_id:
            raise RuntimeOperationError("instance is not running")

        if not self.is_running(state.runtime.container_id):
            raise RuntimeOperationError("instance container is not running")

        self.wait_ready(root, manifest, state, state.inputs)
        checked = replace(
            state,
            last_readiness_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        write_state(root, checked)
        return checked

    def _wait_check(
        self,
        root: Path,
        state: InstanceState,
        check: Check,
        values: Mapping[str, str | int | bool],
    ) -> None:
        identifier = state.runtime.container_id or _container_name(state)
        deadline = time.monotonic() + check.timeout
        last_logs = ""

        while time.monotonic() < deadline:
            if not self.is_running(identifier):
                last_logs = str(self.logs(root))
                _save_readiness_logs(root, check.id, last_logs)
                raise RuntimeOperationError(
                    f"readiness check {check.id} failed: container stopped"
                )

            if check.kind == "process-alive":
                return

            if check.kind == "log-regex" and check.pattern is not None:
                last_logs = str(self.logs(root))

                if re.search(check.pattern, last_logs):
                    _save_readiness_logs(root, check.id, last_logs)
                    return

            if check.kind == "tcp" and check.port is not None:
                host = _interpolate(check.host or "127.0.0.1", values)
                _validate_readiness_host(host)
                port = int(_interpolate(str(check.port), values))

                try:
                    with socket.create_connection((host, port), timeout=0.5):
                        return
                except OSError:
                    pass

            if check.kind == "command" and check.command:
                result = self._run(
                    [
                        "docker",
                        "exec",
                        identifier,
                        *(_interpolate(argument, values) for argument in check.command),
                    ],
                    check=False,
                )

                if result.returncode == 0:
                    return

            time.sleep(0.25)

        if check.kind == "log-regex":
            _save_readiness_logs(root, check.id, last_logs)

        if check.required:
            raise RuntimeOperationError(
                f"readiness check {check.id} timed out", timeout=check.timeout
            )

    def _run(
        self,
        argv: Sequence[str],
        *,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return self._runner(
                argv,
                check=check,
                capture_output=True,
                text=True,
                shell=False,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeOperationError(f"Docker command failed: {exc}") from exc


def build_run_argv(
    root: Path,
    manifest: Manifest,
    image: str,
    container_name: str,
    values: Mapping[str, str | int | bool],
) -> tuple[str, ...]:
    runtime = manifest.runtime
    command = [
        "docker",
        "run",
        "--detach",
        "--interactive",
        "--name",
        container_name,
        "--workdir",
        runtime.workdir,
        "--stop-signal",
        runtime.stop_signal,
    ]

    if runtime.memory is not None:
        memory = _interpolate(runtime.memory, values)

        if not MEMORY_RE.fullmatch(memory):
            raise ValidationError("runtime memory value is invalid")

        command.extend(("--memory", memory.lower()))

    if runtime.read_only_root:
        command.append("--read-only")

    if runtime.run_as is not None:
        command.extend(("--user", _interpolate(runtime.run_as, values)))

    restart = runtime.restart

    if restart not in {"no", "on-failure", "always", "unless-stopped"}:
        raise ValidationError(f"unsupported restart policy: {restart}")

    if restart != "no":
        policy = restart

        if restart == "on-failure" and runtime.restart_limit:
            policy = f"{restart}:{runtime.restart_limit}"

        command.extend(("--restart", policy))

    mounts = runtime.mounts

    if not mounts:
        from luminesk_cli.domain.manifest import RuntimeMount

        mounts = (RuntimeMount(source=".", target=runtime.workdir, mode="rw"),)

    for mount in mounts:
        source = (root / mount.source).resolve()

        if not source.is_relative_to(root):
            raise ValidationError("runtime mount escapes instance root")

        if mount.source != ".":
            source.mkdir(parents=True, exist_ok=True)

        mount_option = f"type=bind,src={source},dst={mount.target}"

        if mount.mode == "ro":
            mount_option += ",readonly"

        command.extend(("--mount", mount_option))

    for port in runtime.ports:
        command.extend(("--publish", _port_mapping(port, values)))

    command.append(image)
    command.extend(_interpolate(argument, values) for argument in runtime.command)
    return tuple(command)


def _port_mapping(
    port: RuntimePort,
    values: Mapping[str, str | int | bool],
) -> str:
    host = _interpolate(str(port.host), values)
    container = _interpolate(str(port.container), values)

    for name, value in (("host", host), ("container", container)):
        try:
            number = int(value)
        except ValueError as exc:
            raise ValidationError(f"runtime {name} port is not an integer") from exc

        if not 1 <= number <= 65535:
            raise ValidationError(f"runtime {name} port is out of range")

    return f"{host}:{container}/{port.protocol}"


def _interpolate(value: str, inputs: Mapping[str, str | int | bool]) -> str:
    pattern = re.compile(r"\$\{input\.([A-Za-z0-9_-]+)\}")

    def replace_input(match: re.Match[str]) -> str:
        name = match.group(1)

        if name not in inputs:
            raise ValidationError(f"runtime references missing input: {name}")

        return str(inputs[name])

    return pattern.sub(replace_input, value)


def _validate_readiness_host(host: str) -> None:
    import ipaddress

    if host.lower() == "localhost":
        return

    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValidationError(
            "TCP readiness host must be localhost or a loopback address"
        ) from exc

    if not address.is_loopback:
        raise ValidationError(
            "TCP readiness host must be localhost or a loopback address"
        )


def _load_instance(root: Path) -> tuple[InstanceState, Manifest, Lockfile]:
    state = load_state(root)

    if state is None:
        raise ValidationError("instance state is missing; run nesk install first")

    lockfile = load_lockfile(root / LOCKFILE_NAME)
    if lockfile.recipe is None:
        manifest = load_manifest(root / "luminesk.toml")
        if manifest.digest != lockfile.manifest_digest:
            raise ValidationError("Installed luminesk.toml differs from luminesk.lock.")
    else:
        manifest = load_verified_installed_recipe(root, lockfile).manifest
    return state, manifest, lockfile


def _container_name(state: InstanceState) -> str:
    normalized = CONTAINER_NAME_RE.sub("-", state.tag.lower()).strip("-._")
    return f"luminesk-{normalized[:32]}-{state.instance_id[:8]}"


def _save_readiness_logs(root: Path, check_id: str, content: str) -> None:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = root / ".luminesk_cli" / "logs" / f"readiness-{check_id}-{timestamp}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content[-1024 * 1024 :], encoding="utf-8", errors="replace")
