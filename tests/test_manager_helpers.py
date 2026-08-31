from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from luminesk_cli.core import manager
from luminesk_cli.core.config import ManagedServer, UserConfig
from luminesk_cli.core.manager import (
    MAX_CORE_DOWNLOAD_BYTES,
    _extract_file_name_from_content_disposition,
    _file_hash_matches,
    _parse_content_length,
    _read_cached_file_name,
    _require_safe_download_file_name,
    _resolve_download_file_name,
    _resolve_download_target_path,
    _sanitize_cache_component,
    _validate_download_size,
    format_timedelta,
)
from luminesk_cli.models.manager import ServerManagerError
from luminesk_cli.models.registry import CoreProvider


def test_format_timedelta() -> None:
    assert format_timedelta(None) == "-"
    assert format_timedelta(timedelta(hours=1, minutes=2, seconds=3)) == "01:02:03"


def test_sanitize_cache_component() -> None:
    assert _sanitize_cache_component("  ..v1.0/rc1.. ") == "v1.0-rc1"
    assert _sanitize_cache_component("   ") == "latest"


def test_read_cached_file_name(tmp_path: Path) -> None:
    metadata_path = tmp_path / "meta.json"
    metadata_path.write_text('{"file_name": "core.jar"}', encoding="utf-8")
    assert _read_cached_file_name(metadata_path) == "core.jar"

    metadata_path.write_text('{"file_name": "dir/core.jar"}', encoding="utf-8")
    assert _read_cached_file_name(metadata_path) is None

    metadata_path.write_text('{"file_name": "core.zip"}', encoding="utf-8")
    assert _read_cached_file_name(metadata_path) is None


def test_extract_file_name_from_content_disposition() -> None:
    assert (
        _extract_file_name_from_content_disposition('attachment; filename="core.jar"')
        == "core.jar"
    )
    assert (
        _extract_file_name_from_content_disposition(
            "attachment; filename*=UTF-8''Lumi%20Core.jar"
        )
        == "Lumi Core.jar"
    )


def test_resolve_download_file_name_rejects_unsafe_content_disposition() -> None:
    response = httpx.Response(
        200,
        headers={"content-disposition": 'attachment; filename="../../outside.jar"'},
        request=httpx.Request("GET", "https://example.com/core.jar"),
    )

    with pytest.raises(ServerManagerError):
        _resolve_download_file_name(
            response, "https://example.com/core.jar", _dummy_core()
        )


def test_require_safe_download_file_name() -> None:
    assert _require_safe_download_file_name("core.jar") == "core.jar"

    for file_name in ("../core.jar", r"..\core.jar", "/tmp/core.jar", "core.zip", ""):
        with pytest.raises(ServerManagerError):
            _require_safe_download_file_name(file_name)


def test_resolve_download_target_path_stays_in_directory(tmp_path: Path) -> None:
    assert (
        _resolve_download_target_path(tmp_path, "core.jar")
        == (tmp_path / "core.jar").resolve()
    )

    with pytest.raises(ServerManagerError):
        _resolve_download_target_path(tmp_path, "../outside.jar")


def test_parse_content_length() -> None:
    assert _parse_content_length(None) is None
    assert _parse_content_length("123") == 123
    assert _parse_content_length("nope") is None
    assert _parse_content_length("-1") is None


def test_validate_download_size() -> None:
    _validate_download_size(MAX_CORE_DOWNLOAD_BYTES)

    with pytest.raises(ServerManagerError):
        _validate_download_size(MAX_CORE_DOWNLOAD_BYTES + 1)


def test_file_hash_matches(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")

    # SHA-1 of "hello world" is 2aae6c35c94fcfb415dbe95f408b9ce91ee846ed
    assert _file_hash_matches(test_file, "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed") is True
    assert _file_hash_matches(test_file, "wronghashwronghashwronghashwronghashwron") is False

    # SHA-256 of "hello world" is b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    assert _file_hash_matches(test_file, "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9") is True
    assert _file_hash_matches(test_file, "wrong" * 12 + "1234") is False



def test_stop_server_stops_docker_container(monkeypatch, tmp_path: Path) -> None:
    config = _running_docker_config(tmp_path)
    calls: list[str] = []

    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)
    monkeypatch.setattr(manager, "docker_container_is_running", lambda _: True)
    monkeypatch.setattr(manager, "get_docker_container_pid", lambda _: 1234)
    monkeypatch.setattr(manager, "get_docker_container_exit_code", lambda _: 0)
    monkeypatch.setattr(
        manager, "remove_docker_container", lambda _: calls.append("rm")
    )
    monkeypatch.setattr(
        manager, "stop_docker_container", lambda name: calls.append(f"stop:{name}")
    )

    result = manager.stop_server(config=config, tag="test", force=True)

    assert result.signal_name == "SIGINT"
    assert calls == ["stop:luminesk_cli-test", "rm"]
    server = config.get_server_by_tag("test")
    assert server is not None
    assert server.runtime.status == "stopped"


def test_stop_server_docker_loop_without_force(monkeypatch, tmp_path: Path) -> None:
    config = _running_docker_config(tmp_path)
    server = config.get_server_by_tag("test")
    assert server is not None
    server.runtime.loop_enabled = True
    calls: list[str] = []

    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)
    monkeypatch.setattr(manager, "docker_container_is_running", lambda _: True)
    monkeypatch.setattr(
        manager, "send_docker_ctrl_c", lambda name: calls.append(f"{name}:ctrl_c")
    )
    monkeypatch.setattr(
        manager, "remove_docker_container", lambda _: calls.append("rm")
    )
    monkeypatch.setattr(
        manager, "stop_docker_container", lambda name: calls.append(f"stop:{name}")
    )

    result = manager.stop_server(config=config, tag="test", force=False)

    assert result.signal_name == "SIGINT"
    assert result.loop_active is True
    assert calls == ["luminesk_cli-test:ctrl_c"]
    assert server.runtime.status == "running"


def test_kill_server_uses_cross_platform_docker_kill(
    monkeypatch, tmp_path: Path
) -> None:
    config = _running_docker_config(tmp_path)
    calls: list[str] = []

    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)
    monkeypatch.setattr(manager, "docker_container_is_running", lambda _: True)
    monkeypatch.setattr(manager, "get_docker_container_pid", lambda _: 1234)
    monkeypatch.setattr(manager, "get_docker_container_exit_code", lambda _: 137)
    monkeypatch.setattr(
        manager, "remove_docker_container", lambda _: calls.append("rm")
    )
    monkeypatch.setattr(
        manager, "kill_docker_container", lambda name: calls.append(f"kill:{name}")
    )

    result = manager.kill_server(config=config, tag="test", force=True)

    assert result.signal_name == "SIGKILL"
    assert calls == ["kill:luminesk_cli-test", "rm"]
    server = config.get_server_by_tag("test")
    assert server is not None
    assert server.runtime.last_exit_code == 137


def test_delete_server_removes_registration_without_deleting_files(
    monkeypatch, tmp_path: Path
) -> None:
    server_dir = tmp_path / "test"
    server_dir.mkdir()
    metadata_dir = server_dir / ".luminesk_cli"
    metadata_dir.mkdir()
    executable_path = server_dir / "server.jar"
    executable_path.write_text("jar", encoding="utf-8")
    server = ManagedServer(
        name="Test",
        tag="test",
        path=server_dir,
        core_id="nukkit",
        executable_name="server.jar",
    )
    config = UserConfig(servers={server.tag: server})
    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)

    deleted = manager.delete_server(config=config, tag="test")

    assert deleted == server
    assert config.get_server_by_tag("test") is None
    assert executable_path.is_file()
    assert not metadata_dir.exists()


def test_delete_server_requires_stopped_server(monkeypatch, tmp_path: Path) -> None:
    config = _running_docker_config(tmp_path)

    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)
    monkeypatch.setattr(manager, "docker_container_is_running", lambda _: True)
    monkeypatch.setattr(manager, "get_docker_container_pid", lambda _: 1234)

    with pytest.raises(ServerManagerError, match="must be stopped"):
        manager.delete_server(config=config, tag="test")

    assert config.get_server_by_tag("test") is not None


def test_change_server_image_requires_stopped_server(
    monkeypatch, tmp_path: Path
) -> None:
    config = _running_docker_config(tmp_path)

    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)
    monkeypatch.setattr(manager, "docker_container_is_running", lambda _: True)
    monkeypatch.setattr(manager, "get_docker_container_pid", lambda _: 1234)

    server = config.get_server_by_tag("test")
    assert server is not None

    with pytest.raises(ServerManagerError, match="must be stopped"):
        manager.change_server_image(
            config=config,
            server=server,
            image="eclipse-temurin:17-jre",
        )


def test_change_server_image_updates_image(monkeypatch, tmp_path: Path) -> None:
    server = ManagedServer(
        name="Test",
        tag="test",
        path=tmp_path,
        core_id="nukkit",
        executable_name="server.jar",
    )
    config = UserConfig(servers={server.tag: server})
    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)
    monkeypatch.setattr("luminesk_cli.utils.docker.docker_image_exists", lambda _: True)

    updated = manager.change_server_image(config=config, server=server, image="eclipse-temurin:17-jre")

    assert updated.runtime_image == "eclipse-temurin:17-jre"


def _running_docker_config(tmp_path: Path) -> UserConfig:
    server = ManagedServer(
        name="Test",
        tag="test",
        path=tmp_path,
        core_id="nukkit",
        executable_name="server.jar",
    )
    config = UserConfig(servers={server.tag: server})
    config.mark_server_started(
        server.tag,
        pid=1234,
        docker_container_id="container-id",
        docker_container_name="luminesk_cli-test",
        docker_memory_limit="1g",
    )
    return config


def _dummy_core() -> CoreProvider:
    return CoreProvider(
        id="dummy",
        name="Dummy",
        description={"en": "Dummy"},
        url="https://example.com",
    )




def test_resolve_server_target_by_directory(tmp_path: Path) -> None:
    server = ManagedServer(
        name="Test",
        tag="test",
        path=tmp_path,
        core_id="nukkit",
        executable_name="server.jar",
    )
    config = UserConfig(servers={server.tag: server})
    target = manager.resolve_server_target(config=config, tag=None, directory=tmp_path)
    assert target.server == server
    assert target.value == "test"

    # Also check with empty string tag
    target_empty = manager.resolve_server_target(config=config, tag="   ", directory=tmp_path)
    assert target_empty.server == server
    assert target_empty.value == "test"


def test_stop_server_by_directory(monkeypatch, tmp_path: Path) -> None:
    config = _running_docker_config(tmp_path)
    calls: list[str] = []

    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)
    monkeypatch.setattr(manager, "docker_container_is_running", lambda _: True)
    monkeypatch.setattr(manager, "get_docker_container_pid", lambda _: 1234)
    monkeypatch.setattr(manager, "get_docker_container_exit_code", lambda _: 0)
    monkeypatch.setattr(
        manager, "remove_docker_container", lambda _: calls.append("rm")
    )
    monkeypatch.setattr(
        manager, "stop_docker_container", lambda name: calls.append(f"stop:{name}")
    )

    result = manager.stop_server(config=config, tag=None, force=True, directory=tmp_path)

    assert result.signal_name == "SIGINT"
    assert calls == ["stop:luminesk_cli-test", "rm"]
    server = config.get_server_by_tag("test")
    assert server is not None
    assert server.runtime.status == "stopped"


def test_delete_server_by_directory(monkeypatch, tmp_path: Path) -> None:
    server_dir = tmp_path / "test"
    server_dir.mkdir()
    metadata_dir = server_dir / ".luminesk_cli"
    metadata_dir.mkdir()
    executable_path = server_dir / "server.jar"
    executable_path.write_text("jar", encoding="utf-8")
    server = ManagedServer(
        name="Test",
        tag="test",
        path=server_dir,
        core_id="nukkit",
        executable_name="server.jar",
    )
    config = UserConfig(servers={server.tag: server})
    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)

    deleted = manager.delete_server(config=config, tag=None, directory=server_dir)

    assert deleted == server
    assert config.get_server_by_tag("test") is None
    assert executable_path.is_file()
    assert not metadata_dir.exists()


def test_upgrade_server_core_missing_hash(monkeypatch, tmp_path: Path) -> None:
    from luminesk_cli.models.manager import DownloadedCore

    server_dir = tmp_path / "test"
    server_dir.mkdir()
    executable_path = server_dir / "server.jar"
    executable_path.write_text("jar", encoding="utf-8")
    server = ManagedServer(
        name="Test",
        tag="test",
        path=server_dir,
        core_id="nukkit",
        executable_name="server.jar",
        core_hash=None,
    )
    config = UserConfig(servers={server.tag: server})
    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)

    # 1. Without redownload: should raise ServerManagerError
    with pytest.raises(ServerManagerError, match="has no managed core hash metadata"):
        manager.upgrade_server_core(config=config, server=server)

    # 2. With redownload: should succeed
    download_calls = []
    def mock_download(core, path, console=None, skip_if_hash=None):
        download_calls.append(skip_if_hash)
        new_exe = path / "server.jar"
        new_exe.write_text("new_jar", encoding="utf-8")
        return DownloadedCore(executable_path=new_exe, hash="new_hash")

    monkeypatch.setattr(manager, "download_core", mock_download)

    updated, upgraded = manager.upgrade_server_core(config=config, server=server, redownload=True)
    assert upgraded is True
    assert updated.core_hash == "new_hash"
    assert download_calls == [None]
    assert executable_path.read_text(encoding="utf-8") == "new_jar"
