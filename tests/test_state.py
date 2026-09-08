from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from luminesk_cli.cli.entry import main
from luminesk_cli.domain.instance import InstanceState, RecipeState, RuntimeState
from luminesk_cli.infrastructure.state import InstanceIndex, write_state


def _state(root: Path, instance_id: str) -> InstanceState:
    return InstanceState(
        instance_id=instance_id,
        name="fixture",
        tag="shared-tag",
        root=str(root),
        applied_lock_digest=f"sha256:{'a' * 64}",
        installed_package_digest=f"sha256:{'b' * 64}",
        recipe=RecipeState(),
        inputs={},
        runtime=RuntimeState(),
        created_at="2026-09-06T00:00:00+00:00",
        updated_at="2026-09-06T00:00:00+00:00",
    )


def test_instance_index_migrates_unique_tags_and_allows_multiple_instances(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.sqlite3"
    first = _state(tmp_path / "first", "11111111-1111-1111-1111-111111111111")
    second = _state(tmp_path / "second", "22222222-2222-2222-2222-222222222222")

    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            CREATE TABLE instances_v2 (
                instance_id TEXT PRIMARY KEY,
                tag TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            "INSERT INTO instances_v2(instance_id, tag, path) VALUES (?, ?, ?)",
            (first.instance_id, first.tag, first.root),
        )
        connection.commit()

    index = InstanceIndex(path)
    index.register(second)

    indexed = tuple(
        (item.instance_id, item.tag, item.path)
        for item in sorted(index.list(), key=lambda item: item.path)
    )
    assert indexed == (
        (first.instance_id, first.tag, first.root),
        (second.instance_id, second.tag, second.root),
    )


def test_instance_index_replaces_stale_entry_for_same_path(tmp_path: Path) -> None:
    index = InstanceIndex(tmp_path / "state.sqlite3")
    root = tmp_path / "instance"
    old = _state(root, "11111111-1111-1111-1111-111111111111")
    current = _state(root, "22222222-2222-2222-2222-222222222222")

    index.register(old)
    index.register(current)

    assert tuple((item.instance_id, item.tag, item.path) for item in index.list()) == (
        (current.instance_id, current.tag, current.root),
    )


def test_list_command_reports_available_and_missing_instances(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    index = InstanceIndex(config_home / "luminesk_cli" / "state.sqlite3")
    available_root = tmp_path / "available"
    available_root.mkdir()
    available = _state(
        available_root,
        "11111111-1111-1111-1111-111111111111",
    )
    missing = _state(
        tmp_path / "missing",
        "22222222-2222-2222-2222-222222222222",
    )
    write_state(available_root, available)
    index.register(missing)
    index.register(available)

    assert main(["list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["count"] == 2
    assert payload["instances"] == [
        {
            "available": True,
            "instanceId": available.instance_id,
            "path": str(available_root),
            "recordedStatus": "stopped",
            "tag": "shared-tag",
        },
        {
            "available": False,
            "instanceId": missing.instance_id,
            "path": str(tmp_path / "missing"),
            "recordedStatus": "missing",
            "tag": "shared-tag",
        },
    ]


def test_list_command_explains_how_to_rebuild_empty_index(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    assert main(["list"]) == 0

    assert "nesk import PATH --scan" in capsys.readouterr().out
