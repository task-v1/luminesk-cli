from __future__ import annotations

from typing import Any

from luminesk_cli.cli.commands.common import emit, recipe, resolve_lock
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, write_lockfile


def run(namespace: Any) -> int:
    root, manifest = recipe(namespace.dir)
    lockfile = resolve_lock(root, manifest, frozen=False)
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
