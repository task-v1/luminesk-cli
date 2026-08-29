from __future__ import annotations

from typing import Any

from luminesk_cli.application.install import TransactionalInstaller
from luminesk_cli.cli.commands.common import (
    build_package,
    emit,
    parse_inputs,
    recipe,
    resolve_lock,
)


def run(namespace: Any) -> int:
    root, manifest = recipe(namespace.dir)
    lockfile = resolve_lock(root, manifest, frozen=namespace.frozen)
    values = parse_inputs(manifest, namespace.set)
    temporary, package = build_package(root, manifest, lockfile, values)

    try:
        plan = TransactionalInstaller().plan(package, root)
    finally:
        temporary.cleanup()

    changes = [
        {
            "action": change.action,
            "path": change.path,
            "reason": change.reason,
        }
        for change in plan.changes
    ]
    lines = [f"Plan for {plan.target}:"]
    lines.extend(
        f"  {change.action:8} {change.path} — {change.reason}"
        for change in plan.changes
    )
    emit(namespace, {"plan": {"operation": plan.operation, "changes": changes}}, "\n".join(lines))
    return 0
