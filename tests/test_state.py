from __future__ import annotations

import sqlite3
from pathlib import Path

from luminesk_cli.domain.instance import InstanceState, RecipeState, RuntimeState
from luminesk_cli.infrastructure.state import InstanceIndex


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

    with sqlite3.connect(path) as connection:
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
