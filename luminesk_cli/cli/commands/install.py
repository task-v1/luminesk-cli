from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from luminesk_cli.application.install import TransactionalInstaller
from luminesk_cli.application.recipe_update import record_recipe_ownership
from luminesk_cli.cli.commands.common import (
    build_package,
    emit,
    index_path,
    parse_inputs,
    recipe,
    resolve_lock,
)
from luminesk_cli.domain.errors import ConflictError, ValidationError
from luminesk_cli.infrastructure.recipe import (
    RecipeCheckout,
    checkout_recipe,
    cleanup_materialized,
    ensure_empty_target,
    materialize_checkout,
    materialize_local_recipe,
    normalize_git_source,
)
from luminesk_cli.infrastructure.state import (
    RECIPE_OWNERSHIP_FILE,
    InstanceIndex,
    state_directory,
)


def run(namespace: Any) -> int:
    if namespace.source is None:
        target = Path(namespace.dir or ".").expanduser().resolve()
        return _install_local(namespace, target)

    source_path = Path(namespace.source).expanduser()

    if source_path.exists():
        recipe_root = source_path.resolve()
        target = Path(namespace.dir or ".").expanduser().resolve()

        if recipe_root == target:
            return _install_local(namespace, target)

        ensure_empty_target(target)
        return _install_external_local(namespace, recipe_root, target)

    if namespace.frozen:
        raise ValidationError("remote Git install cannot resolve a recipe with --frozen")

    target = Path(namespace.dir or ".").expanduser().resolve()
    ensure_empty_target(target)
    source = normalize_git_source(namespace.source, namespace.ref)

    with tempfile.TemporaryDirectory(prefix="nesk-recipe-") as temporary:
        checkout = checkout_recipe(
            source,
            Path(temporary) / "recipe",
            require_git=namespace.keep_git,
        )
        return _install_checkout(namespace, checkout, target)


def _install_local(namespace: Any, target: Path) -> int:
    root, manifest = recipe(target)
    lockfile = resolve_lock(root, manifest, frozen=namespace.frozen)
    values = parse_inputs(manifest, namespace.set)
    temporary, package = build_package(root, manifest, lockfile, values)

    try:
        installer = TransactionalInstaller(index=InstanceIndex(index_path()))
        plan, state = installer.install(
            manifest,
            lockfile,
            package,
            target,
            inputs=values,
            dry_run=namespace.dry_run,
        )
    finally:
        temporary.cleanup()

    return _emit_result(namespace, plan, state)


def _install_external_local(namespace: Any, recipe_root: Path, target: Path) -> int:
    root, manifest = recipe(recipe_root)
    lockfile = resolve_lock(root, manifest, frozen=namespace.frozen)
    values = parse_inputs(manifest, namespace.set)
    temporary, package = build_package(root, manifest, lockfile, values)

    try:
        if namespace.dry_run:
            plan = TransactionalInstaller().plan(package, target)
            return _emit_result(namespace, plan, None)

        _confirm(namespace, manifest.package.name, target, "local", lockfile)
        copied = materialize_local_recipe(recipe_root, target)

        try:
            plan, state = TransactionalInstaller(
                index=InstanceIndex(index_path())
            ).install(manifest, lockfile, package, target, inputs=values)
        except BaseException:
            cleanup_materialized(target, copied)
            raise

        return _emit_result(namespace, plan, state)
    finally:
        temporary.cleanup()


def _install_checkout(
    namespace: Any,
    checkout: RecipeCheckout,
    target: Path,
) -> int:
    root, manifest = recipe(checkout.root)
    lockfile = resolve_lock(
        root,
        manifest,
        frozen=False,
        recipe_source=checkout.source.canonical,
        recipe_revision=checkout.revision,
        recipe_ref=checkout.tracking_ref or checkout.source.requested_ref,
        recipe_tracking=checkout.tracking_ref is not None,
    )
    values = parse_inputs(manifest, namespace.set)
    temporary, package = build_package(root, manifest, lockfile, values)

    try:
        plan = TransactionalInstaller().plan(package, target)

        if namespace.dry_run:
            return _emit_result(namespace, plan, None)

        _confirm(namespace, manifest.package.name, target, "direct", lockfile)
        copied = materialize_checkout(
            checkout,
            target,
            keep_git=namespace.keep_git,
        )
        record_recipe_ownership(checkout, target)

        try:
            plan, state = TransactionalInstaller(
                index=InstanceIndex(index_path())
            ).install(manifest, lockfile, package, target, inputs=values)
        except BaseException:
            (state_directory(target) / RECIPE_OWNERSHIP_FILE).unlink(missing_ok=True)
            cleanup_materialized(target, copied)
            raise

        return _emit_result(namespace, plan, state)
    finally:
        temporary.cleanup()


def _confirm(
    namespace: Any,
    package_name: str,
    target: Path,
    trust: str,
    lockfile: Any,
) -> None:
    build_enabled = lockfile.build is not None
    summary = (
        f"Source package: {package_name}\n"
        f"Trust: {trust}\n"
        f"Revision: {lockfile.recipe.revision if lockfile.recipe else 'local'}\n"
        f"Build code: {'declared' if build_enabled else 'none/remote artifacts'}\n"
        f"Writes: {target}\n"
        f"Downloads: {len(lockfile.sources)} artifact(s)"
    )

    if not namespace.json:
        print(summary)

    if namespace.yes:
        return

    if namespace.non_interactive or namespace.json:
        raise ConflictError("remote install requires --yes in non-interactive mode")

    answer = input("Continue? [y/N] ").strip().lower()

    if answer not in {"y", "yes"}:
        raise ConflictError("installation was not confirmed")


def _emit_result(namespace: Any, plan: Any, state: Any) -> int:
    payload = {
        "operation": plan.operation,
        "target": plan.target,
        "dryRun": state is None,
        "instanceId": state.instance_id if state is not None else None,
        "changes": [
            {"action": item.action, "path": item.path, "reason": item.reason}
            for item in plan.changes
        ],
    }
    verb = "Planned" if state is None else "Installed"
    emit(namespace, payload, f"{verb} {plan.target} ({len(plan.changes)} changes)")
    return 0
