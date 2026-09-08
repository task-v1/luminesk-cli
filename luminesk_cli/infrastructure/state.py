"""Atomic local state persistence and rebuildable global instance index."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from luminesk_cli.domain.instance import (
    InstanceState,
    OwnershipLedger,
    parse_ownership,
    parse_state,
)

LOCAL_STATE_DIRECTORY = ".luminesk_cli"
STATE_FILE = "state.json"
OWNERSHIP_FILE = "ownership.json"
RECIPE_DIRECTORY = "recipe"
LOGGER = logging.getLogger(__name__)

INSTANCE_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS instances_v2 (
    instance_id TEXT PRIMARY KEY,
    tag TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE
)
"""


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary, path)

        if hasattr(os, "O_DIRECTORY"):
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)

            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def state_directory(root: Path) -> Path:
    return root / LOCAL_STATE_DIRECTORY


def load_state(root: Path) -> InstanceState | None:
    path = state_directory(root) / STATE_FILE

    if not path.exists():
        return None

    return parse_state(path.read_bytes())


def write_state(root: Path, state: InstanceState) -> None:
    atomic_write(
        state_directory(root) / STATE_FILE,
        canonical_json_bytes(state.to_dict()),
    )


def load_ownership(root: Path) -> OwnershipLedger:
    path = state_directory(root) / OWNERSHIP_FILE

    if not path.exists():
        return OwnershipLedger(files={})

    return parse_ownership(path.read_bytes())


def write_ownership(root: Path, ledger: OwnershipLedger) -> None:
    atomic_write(
        state_directory(root) / OWNERSHIP_FILE,
        canonical_json_bytes(ledger.to_dict()),
    )


@dataclass(slots=True, frozen=True)
class IndexedInstance:
    instance_id: str
    tag: str
    path: str


class InstanceIndex:
    """A disposable lookup index; local state remains authoritative."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def register(self, state: InstanceState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self.path, timeout=30)) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=30000")
            _ensure_instance_index_schema(connection)
            connection.execute(
                "DELETE FROM instances_v2 WHERE path = ? AND instance_id != ?",
                (state.root, state.instance_id),
            )
            connection.execute(
                """
                INSERT INTO instances_v2(instance_id, tag, path)
                VALUES (?, ?, ?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    tag = excluded.tag,
                    path = excluded.path
                """,
                (state.instance_id, state.tag, state.root),
            )
            connection.commit()

    def list(self) -> tuple[IndexedInstance, ...]:
        if not self.path.exists():
            return ()

        with closing(sqlite3.connect(self.path, timeout=30)) as connection:
            _ensure_instance_index_schema(connection)
            rows = connection.execute(
                "SELECT instance_id, tag, path FROM instances_v2 ORDER BY tag, path"
            ).fetchall()

        return tuple(IndexedInstance(*row) for row in rows)


def _ensure_instance_index_schema(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'instances_v2'"
        ).fetchone()

        if row is None:
            connection.execute(INSTANCE_INDEX_SCHEMA)
            connection.commit()
            return

        if not _instance_index_has_unique_tag(connection):
            connection.commit()
            return

        LOGGER.debug("instance index schema migration started version=2")
        connection.execute("ALTER TABLE instances_v2 RENAME TO instances_v2_unique_tag")
        connection.execute(INSTANCE_INDEX_SCHEMA)
        connection.execute(
            """
            INSERT INTO instances_v2(instance_id, tag, path)
            SELECT instance_id, tag, path FROM instances_v2_unique_tag
            """
        )
        connection.execute("DROP TABLE instances_v2_unique_tag")
    except BaseException:
        connection.rollback()
        raise
    connection.commit()
    LOGGER.debug("instance index schema migration completed version=2")


def _instance_index_has_unique_tag(connection: sqlite3.Connection) -> bool:
    for index in connection.execute("PRAGMA index_list(instances_v2)").fetchall():
        if not bool(index[2]):
            continue

        index_name = str(index[1])
        columns = connection.execute(
            "SELECT name FROM pragma_index_info(?)",
            (index_name,),
        ).fetchall()
        if [str(column[0]) for column in columns] == ["tag"]:
            return True

    return False
