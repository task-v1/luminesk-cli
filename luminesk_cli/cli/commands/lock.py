from __future__ import annotations

from typing import Any

from luminesk_cli.cli.commands.common import emit, recipe, resolve_lock
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, write_lockfile
from luminesk_cli.infrastructure.recipe_snapshot import create_recipe_snapshot


def run(namespace: Any) -> int:
    root, manifest = recipe(namespace.dir)
    snapshot = create_recipe_snapshot(root, manifest)
    lockfile = resolve_lock(
        root,
        manifest,
        frozen=namespace.frozen,
        recipe_origin=snapshot.origin,
    )
    path = root / LOCKFILE_NAME
    write_lockfile(path, lockfile)
    emit(
        namespace,
        {
            "lockfile": str(path),
            "digest": lockfile.digest,
            "sources": len(lockfile.sources),
        },
        f"Locked {len(lockfile.sources)} source(s) to {path}",
    )
    return 0
