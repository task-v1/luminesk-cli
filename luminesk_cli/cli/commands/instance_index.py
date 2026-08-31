from __future__ import annotations

from pathlib import Path
from typing import Any

from luminesk_cli.cli.commands.common import emit, index_path
from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.infrastructure.state import InstanceIndex, load_state

MAX_SCAN_STATES = 10_000


def import_instances(namespace: Any) -> int:
    start = Path(namespace.path).expanduser().resolve()
    roots = _scan(start) if namespace.scan else (start,)
    index = InstanceIndex(index_path())
    imported = []

    for root in roots:
        state = load_state(root)

        if state is None:
            if namespace.scan:
                continue

            raise ValidationError(f"instance state is missing: {root}")

        if Path(state.root).resolve() != root:
            raise ValidationError(
                "instance root marker does not match import path",
                recorded=state.root,
                actual=str(root),
            )

        index.register(state)
        imported.append(
            {"instanceId": state.instance_id, "tag": state.tag, "path": str(root)}
        )

    emit(
        namespace,
        {"instances": imported, "count": len(imported)},
        f"Imported {len(imported)} instance(s).",
    )
    return 0


def _scan(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        raise ValidationError(f"scan root is not a directory: {root}")

    states = []

    for path in root.rglob("state.json"):
        if path.parent.name != ".luminesk_cli" or path.is_symlink():
            continue

        states.append(path.parent.parent.resolve())

        if len(states) > MAX_SCAN_STATES:
            raise ValidationError("instance scan found too many state files")

    return tuple(sorted(set(states)))
