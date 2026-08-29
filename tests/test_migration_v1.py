from __future__ import annotations

import json
from pathlib import Path

import pytest

from luminesk_cli.domain.errors import RuntimeOperationError
from luminesk_cli.infrastructure.state import load_ownership, load_state
from luminesk_cli.migration.v1 import V1Migrator


def make_legacy_instance(tmp_path: Path, *, running: bool = False) -> Path:
    root = tmp_path / "legacy-server"
    metadata = root / ".luminesk_cli"
    metadata.mkdir(parents=True)
    (root / "server.jar").write_bytes(b"legacy server")
    (root / "server.properties").write_text(
        "server-port=19140\n", encoding="utf-8"
    )
    (root / "worlds").mkdir()
    (root / "plugins").mkdir()
    (metadata / "core.json").write_text(
        json.dumps(
            {
                "name": "Legacy Server",
                "tag": "legacy",
                "path": str(root),
                "core_id": "nukkit",
                "core_hash": "latest",
                "executable_name": "server.jar",
                "config_file": "server.properties",
                "port_way": "server-port",
                "runtime_image": f"example/server@sha256:{'a' * 64}",
                "memory_limit": "2g",
                "runtime": {"status": "running" if running else "stopped"},
            }
        ),
        encoding="utf-8",
    )
    return root


def test_migration_dry_run_writes_nothing(tmp_path: Path) -> None:
    root = make_legacy_instance(tmp_path)

    report = V1Migrator().migrate(root, dry_run=True)

    assert report.dry_run is True
    assert report.files_owned == 4
    assert report.warnings
    assert not (root / "luminesk.toml").exists()
    assert not (root / "luminesk.lock").exists()
    assert not (root / ".luminesk_cli/state.json").exists()


def test_migration_preserves_data_and_is_idempotent(tmp_path: Path) -> None:
    root = make_legacy_instance(tmp_path)
    original_server = (root / "server.jar").read_bytes()
    original_config = (root / "server.properties").read_bytes()
    migrator = V1Migrator()

    report = migrator.migrate(root)

    assert report.dry_run is False
    assert (root / "server.jar").read_bytes() == original_server
    assert (root / "server.properties").read_bytes() == original_config
    assert (root / "worlds").is_dir()
    assert (root / "plugins").is_dir()
    assert (root / "luminesk.toml").is_file()
    assert (root / "luminesk.lock").is_file()
    assert (root / ".luminesk_cli/core.json").is_file()
    state = load_state(root)
    ownership = load_ownership(root)
    assert state is not None
    assert state.inputs == {"memory": "2g", "port": 19140}
    assert ownership.files["worlds"].mode == "data"
    assert ownership.files["plugins"].mode == "data"

    second = migrator.migrate(root)
    assert second.already_migrated is True
    assert (root / "server.jar").read_bytes() == original_server


def test_running_legacy_instance_is_not_migrated(tmp_path: Path) -> None:
    root = make_legacy_instance(tmp_path, running=True)

    with pytest.raises(RuntimeOperationError, match="running"):
        V1Migrator().migrate(root)

    assert not (root / "luminesk.toml").exists()
