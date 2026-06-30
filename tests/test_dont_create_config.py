from pathlib import Path

from luminesk.core import manager
from luminesk.core.base import JavaCore
from luminesk.core.config import UserConfig
from luminesk.models.manager import DownloadedCore


class DummyDontCreateConfigCore(JavaCore):
    id = "dummy_dont_create"
    name = "Dummy"
    description = {"en": "Dummy description"}
    dont_create_config = True
    config_file = "custom.properties"

    def download(self, target_directory: Path, console=None, skip_if_hash=None) -> DownloadedCore:
        exec_path = target_directory / "server.jar"
        exec_path.touch()
        return DownloadedCore(executable_path=exec_path, hash="1.0")


def test_dont_create_config_bypasses_file_creation_and_setup_check(tmp_path: Path, monkeypatch) -> None:
    # Set up config database
    config = UserConfig(servers={}, db_path=tmp_path / "state.sqlite3")
    core = DummyDontCreateConfigCore()

    # Stub registry config directory creation
    monkeypatch.setattr(manager.UserConfig, "save", lambda self: None)

    # 1. Test create_server does not create the config file
    server = manager.create_server(
        config=config,
        name="Test Server",
        tag="test-server",
        directory=tmp_path / "server_dir",
        core=core,
    )

    config_path = server.path / core.config_file
    assert not config_path.exists(), "Config file should not be created when dont_create_config is True"

    # 2. Test is_server_setup_completed returns True
    assert manager.is_server_setup_completed(server, core) is True, \
        "is_server_setup_completed should return True when dont_create_config is True"
