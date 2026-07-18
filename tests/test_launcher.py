import subprocess
from pathlib import Path

import pytest

from luminesk_cli.core import launcher
from luminesk_cli.core.config import ManagedServer, UserConfig


def test_launch_server_detached_marks_docker_runtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    server = ManagedServer(
        name="Test",
        tag="test",
        path=tmp_path,
        core_id="nukkit",
        executable_name="server.jar",
        runtime_image="eclipse-temurin:17-jre",
    )
    config = UserConfig(
        servers={server.tag: server}, db_path=tmp_path / "state.sqlite3"
    )
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="container-id\n"
        )

    monkeypatch.setattr(launcher, "get_docker_binary", lambda: "docker")
    monkeypatch.setattr(launcher, "docker_container_is_running", lambda _: False)
    monkeypatch.setattr(launcher, "remove_docker_container", lambda _: None)
    monkeypatch.setattr(launcher, "get_docker_container_pid", lambda _: 1234)
    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    result = launcher.launch_server_detached(
        server,
        memory_limit="768m",
        config=config,
    )

    updated_server = config.get_server_by_tag(server.tag)
    assert updated_server is not None
    assert result.container_id == "container-id"
    assert result.container_name == "luminesk_cli-test"
    assert result.memory_limit == "768m"
    assert result.runtime_image == "eclipse-temurin:17-jre"
    assert "eclipse-temurin:17-jre" in calls[-1]
    assert updated_server.memory_limit == "768m"
    assert updated_server.runtime.pid == 1234
    assert updated_server.runtime.docker_container_id == "container-id"
    assert updated_server.runtime.docker_container_name == "luminesk_cli-test"
    assert updated_server.runtime.docker_memory_limit == "768m"


def test_launch_server_detached_surfaces_docker_stderr(
    monkeypatch,
    tmp_path: Path,
) -> None:
    server = ManagedServer(
        name="Test",
        tag="test",
        path=tmp_path,
        core_id="nukkit",
        executable_name="server.jar",
    )

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="docker daemon is not running\n",
        )

    monkeypatch.setattr(launcher, "get_docker_binary", lambda: "docker")
    monkeypatch.setattr(launcher, "docker_container_is_running", lambda _: False)
    monkeypatch.setattr(launcher, "remove_docker_container", lambda _: None)
    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="docker daemon is not running"):
        launcher.launch_server_detached(
            server,
            config=UserConfig(
                servers={server.tag: server}, db_path=tmp_path / "state.sqlite3"
            ),
        )
