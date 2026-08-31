from pathlib import Path

import pytest

from luminesk_cli.utils.docker import (
    DOCKER_SERVER_DIR,
    build_docker_container_name,
    build_docker_run_command,
    normalize_memory_limit,
    normalize_runtime_image,
)


class LaunchTarget:
    tag: str = "My Server!"
    path: Path = Path("/srv/my server")
    executable_name: str = "server.jar"
    core_id: str = "nukkit"
    config_file: str = "server.properties"
    port_way: str = "server-port"


def test_build_docker_container_name_sanitizes_tag() -> None:
    assert build_docker_container_name(" My Server! ") == "luminesk_cli-my-server"


def test_normalize_memory_limit() -> None:
    assert normalize_memory_limit(" 512M ") == "512m"
    assert normalize_memory_limit(None) == "1g"

    for value in ("", "0", "-1g", "one-gigabyte", "1gb"):
        with pytest.raises(ValueError):
            normalize_memory_limit(value)


def test_normalize_runtime_image() -> None:
    assert normalize_runtime_image(None) == "latest"
    assert normalize_runtime_image("17") == "17"
    assert (
        normalize_runtime_image("ghcr.io/example/java:21") == "ghcr.io/example/java:21"
    )

    for value in ("", "java 21"):
        with pytest.raises(ValueError):
            normalize_runtime_image(value)


def test_build_docker_run_command_uses_memory_and_mount(monkeypatch) -> None:
    monkeypatch.setattr("luminesk_cli.utils.docker.platform.system", lambda: "Linux")

    command = build_docker_run_command(
        LaunchTarget(),
        Path("/srv/my server/.luminesk/logs/my-server.log"),
        image="eclipse-temurin:17-jre",
        memory_limit="2g",
        loop=True,
    )

    assert command[:2] == ("docker", "run")
    assert "--memory" in command
    assert command[command.index("--memory") + 1] == "2g"
    assert "--network" in command
    assert command[command.index("--network") + 1] == "host"
    assert "--volume" in command
    mount_source = str(LaunchTarget.path.expanduser().resolve()).replace("\\", "/")
    assert (
        command[command.index("--volume") + 1] == f"{mount_source}:{DOCKER_SERVER_DIR}"
    )
    assert "LUMINESK_LOOP=1" in command
    assert "eclipse-temurin:17-jre" in command


def test_build_docker_run_command_publishes_default_ports_off_linux(
    monkeypatch,
) -> None:
    monkeypatch.setattr("luminesk_cli.utils.docker.platform.system", lambda: "Windows")

    command = build_docker_run_command(
        LaunchTarget(),
        Path("/srv/my server/.luminesk/logs/my-server.log"),
        memory_limit="2g",
    )

    assert "--network" not in command
    assert "19132:19132/udp" in command
    assert "19132:19132/tcp" in command


def test_build_docker_run_command_parses_custom_ports_from_config(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("luminesk_cli.utils.docker.platform.system", lambda: "Windows")

    # 1. Test properties config
    class PropertiesLaunchTarget:
        tag: str = "test-properties"
        path: Path = tmp_path / "prop_server"
        executable_name: str = "server.jar"
        config_file: str = "server.properties"
        port_way: str = "server-port"
        core_id: str = "nukkit"

    PropertiesLaunchTarget.path.mkdir()
    (PropertiesLaunchTarget.path / "server.properties").write_text(
        "motd=Test\nserver-port=25565\nxbox-auth=on", encoding="utf-8"
    )

    command = build_docker_run_command(
        PropertiesLaunchTarget(),
        PropertiesLaunchTarget.path / ".luminesk_cli" / "logs" / "my-server.log",
        memory_limit="2g",
    )
    assert "25565:25565/udp" in command
    assert "25565:25565/tcp" in command

    # 2. Test yml config
    class YmlLaunchTarget:
        tag: str = "test-yml"
        path: Path = tmp_path / "yml_server"
        executable_name: str = "server.jar"
        config_file: str = "settings.yml"
        port_way: str = "general.server-port"
        core_id: str = "nukkit"

    YmlLaunchTarget.path.mkdir()
    (YmlLaunchTarget.path / "settings.yml").write_text(
        "general:\n  server-port: 19135\n  max-players: 20", encoding="utf-8"
    )

    command2 = build_docker_run_command(
        YmlLaunchTarget(),
        YmlLaunchTarget.path / ".luminesk_cli" / "logs" / "my-server.log",
        memory_limit="2g",
    )
    assert "19135:19135/udp" in command2
    assert "19135:19135/tcp" in command2


def test_validate_runtime_image(monkeypatch) -> None:
    from luminesk_cli.utils.docker import validate_runtime_image

    # Mock docker_image_exists to return True unless the image is "nonexistent"
    monkeypatch.setattr("luminesk_cli.utils.docker.docker_image_exists", lambda img: img != "nonexistent")

    # Valid image names
    assert validate_runtime_image("eclipse-temurin:21-jre") == "eclipse-temurin:21-jre"
    assert validate_runtime_image("ubuntu") == "ubuntu"

    # Version-only images should raise ValueError
    with pytest.raises(ValueError, match="version"):
        validate_runtime_image("21")

    with pytest.raises(ValueError, match="version"):
        validate_runtime_image("17.0.1")

    with pytest.raises(ValueError, match="version"):
        validate_runtime_image("21-jre")

    # Non-existent images should raise ValueError
    with pytest.raises(ValueError, match="not found"):
        validate_runtime_image("nonexistent")
