from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from luminesk_cli.cli.commands.common import emit, index_path
from luminesk_cli.domain.errors import ConflictError, ValidationError
from luminesk_cli.infrastructure.state import InstanceIndex, load_state, state_directory
from luminesk_cli.migration.v1 import V1Migrator


def run(namespace: Any) -> int:
    legacy_database = index_path()

    if namespace.cleanup:
        return _cleanup(namespace, legacy_database)

    report = V1Migrator(
        legacy_database=legacy_database,
        index=InstanceIndex(index_path()),
    ).migrate(namespace.identifier, dry_run=namespace.dry_run)
    emit(
        namespace,
        {
            "root": report.root,
            "coreId": report.core_id,
            "manifest": report.manifest,
            "lockfile": report.lockfile,
            "filesOwned": report.files_owned,
            "warnings": list(report.warnings),
            "dryRun": report.dry_run,
            "alreadyMigrated": report.already_migrated,
        },
        ("Migration plan" if report.dry_run else "Migrated")
        + f" {report.root} ({report.core_id})"
        + ("\n" + "\n".join(f"warning: {item}" for item in report.warnings) if report.warnings else ""),
    )
    return 0


def _cleanup(namespace: Any, legacy_database: Path) -> int:
    identifier = Path(namespace.identifier).expanduser()

    if not identifier.exists():
        raise ValidationError("--cleanup requires an explicit migrated instance path")

    root = identifier.resolve()

    if load_state(root) is None:
        raise ConflictError("instance must be migrated successfully before --cleanup")

    legacy = state_directory(root) / "core.json"

    if not legacy.is_file():
        emit(namespace, {"archived": None}, "Legacy metadata is already absent.")
        return 0

    archive = state_directory(root) / "backups" / "legacy-core.json"

    if namespace.dry_run:
        emit(namespace, {"archived": str(archive), "dryRun": True}, f"Would archive {legacy} to {archive}")
        return 0

    archive.parent.mkdir(parents=True, exist_ok=True)

    if archive.exists():
        raise ConflictError(f"legacy metadata backup already exists: {archive}")

    shutil.move(legacy, archive)
    emit(namespace, {"archived": str(archive)}, f"Archived legacy metadata to {archive}")
    return 0
