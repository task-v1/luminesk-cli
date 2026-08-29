from __future__ import annotations

import subprocess
from pathlib import Path

from luminesk_cli.application.runtime import DockerRuntime, build_run_argv
from luminesk_cli.domain.instance import (
    InstanceState,
    RecipeState,
    RuntimeState,
)
from luminesk_cli.domain.lockfile import Lockfile, RuntimeLock, write_lockfile
from luminesk_cli.domain.manifest import load_manifest
from luminesk_cli.infrastructure.state import load_state, write_state

MANIFEST = '''\
manifest_version = 1
[package]
name = "runtime-fixture"
version = "1.0.0"
[inputs.port]
type = "integer"
default = 19132
[[sources]]
id = "core"
provider = "http"
url = "https://example.org/server.jar"
target = "server.jar"
[runtime]
driver = "docker"
image = "example/server:latest"
command = ["java", "-jar", "server.jar; echo not-a-shell"]
workdir = "/server"
memory = "1g"
run_as = "1000:1000"
read_only_root = true
restart = "on-failure"
restart_limit = 3
[[runtime.mounts]]
source = "."
target = "/server"
mode = "rw"
[[runtime.ports]]
name = "bedrock"
host = "${input.port}"
container = "${input.port}"
protocol = "udp"
[[checks]]
id = "ready"
phase = "readiness"
kind = "log-regex"
pattern = "Done"
timeout = 2
'''


def prepare_instance(root: Path) -> tuple[Lockfile, InstanceState]:
    root.mkdir()
    (root / "luminesk.toml").write_text(MANIFEST, encoding="utf-8")
    manifest = load_manifest(root / "luminesk.toml")
    lockfile = Lockfile(
        manifest_digest=manifest.digest,
        target="linux/amd64",
        sources={},
        runtime=RuntimeLock(
            image=f"example/server@sha256:{'a' * 64}"
        ),
    )
    write_lockfile(root / "luminesk.lock", lockfile)
    state = InstanceState(
        instance_id="12345678-1234-1234-1234-123456789abc",
        name="runtime-fixture",
        tag="runtime-fixture",
        root=str(root),
        applied_lock_digest=lockfile.digest,
        installed_package_digest=f"sha256:{'b' * 64}",
        recipe=RecipeState(),
        inputs={"port": 19132},
        runtime=RuntimeState(),
        created_at="2026-08-29T00:00:00+00:00",
        updated_at="2026-08-29T00:00:00+00:00",
    )
    write_state(root, state)
    return lockfile, state


def test_runtime_command_keeps_shell_metacharacters_in_one_argv_element(
    tmp_path: Path,
) -> None:
    root = tmp_path / "instance"
    lockfile, _ = prepare_instance(root)
    manifest = load_manifest(root / "luminesk.toml")

    argv = build_run_argv(
        root,
        manifest,
        lockfile.runtime.image,
        "nesk-fixture",
        {"port": 19132},
    )

    assert "sh" not in argv
    assert "-c" not in argv
    assert argv[-3:] == (
        "java",
        "-jar",
        "server.jar; echo not-a-shell",
    )
    assert "19132:19132/udp" in argv
    assert lockfile.runtime.image in argv


def test_runtime_start_records_container_and_readiness(tmp_path: Path) -> None:
    root = tmp_path / "instance"
    prepare_instance(root)
    calls = []

    def runner(argv, **kwargs):
        calls.append(tuple(argv))

        if argv[1] == "run":
            return subprocess.CompletedProcess(argv, 0, "container-id\n", "")

        if argv[1] == "inspect":
            return subprocess.CompletedProcess(argv, 0, "true\n", "")

        if argv[1] == "logs":
            return subprocess.CompletedProcess(argv, 0, "Done loading\n", "")

        return subprocess.CompletedProcess(argv, 0, "", "")

    state = DockerRuntime(runner=runner).start(root)

    assert state.runtime.status == "running"
    assert state.runtime.container_id == "container-id"
    assert state.last_readiness_at is not None
    assert load_state(root) == state
    run_call = next(call for call in calls if call[1] == "run")
    assert run_call[-1] == "server.jar; echo not-a-shell"
