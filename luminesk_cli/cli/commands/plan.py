from __future__ import annotations

from typing import Any

from luminesk_cli.application.install import TransactionalInstaller
from luminesk_cli.cli.commands.common import (
    build_package,
    cache,
    emit,
    parse_inputs,
    recipe,
    resolve_lock,
    validate_frozen_lock,
)
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, load_lockfile
from luminesk_cli.infrastructure.recipe_snapshot import load_verified_installed_recipe
from luminesk_cli.infrastructure.state import load_state


def run(namespace: Any) -> int:
    target, manifest = recipe(namespace.dir)
    recipe_root = target
    state = load_state(target)
    if state is not None:
        installed_lock = load_lockfile(target / LOCKFILE_NAME)
        snapshot = load_verified_installed_recipe(target, installed_lock)
        recipe_root = snapshot.root
        manifest = snapshot.manifest
        lockfile = (
            validate_frozen_lock(
                installed_lock,
                manifest,
                cache(),
                recipe_origin=snapshot.origin,
            )
            if namespace.frozen
            else resolve_lock(
                recipe_root,
                manifest,
                frozen=False,
                recipe_origin=snapshot.origin,
            )
        )
    else:
        lockfile = resolve_lock(recipe_root, manifest, frozen=namespace.frozen)
    values = parse_inputs(manifest, namespace.set)
    temporary, package = build_package(recipe_root, manifest, lockfile, values)

    try:
        plan = TransactionalInstaller().plan(package, target)
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
    emit(
        namespace,
        {"plan": {"operation": plan.operation, "changes": changes}},
        "\n".join(lines),
    )
    return 0
