from __future__ import annotations

import difflib
import json
import tempfile
from pathlib import Path
from typing import Any

from luminesk_cli.application.install import restore_install_backup
from luminesk_cli.application.recipe_update import restore_recipe_backup
from luminesk_cli.application.update import UpdateService
from luminesk_cli.cli.commands.common import (
    build_package,
    emit,
    parse_inputs,
    recipe,
    resolve_lock,
)
from luminesk_cli.cli.commands.runtime import _instance_root
from luminesk_cli.domain.errors import ConflictError, TransactionError, ValidationError
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, Lockfile, load_lockfile
from luminesk_cli.domain.manifest import MANIFEST_NAME, Manifest, load_manifest
from luminesk_cli.infrastructure.cache import digest_file
from luminesk_cli.infrastructure.recipe import (
    RecipeCheckout,
    checkout_recipe,
    normalize_git_source,
)
from luminesk_cli.infrastructure.state import (
    load_ownership,
    state_directory,
)


def run(namespace: Any) -> int:
    root = _instance_root(namespace.dir)
    old_lock = load_lockfile(root / LOCKFILE_NAME)

    with tempfile.TemporaryDirectory(prefix="nesk-update-recipe-") as temporary:
        checkout = _updated_checkout(old_lock, Path(temporary) / "recipe")
        recipe_source: str | None
        recipe_revision: str | None
        recipe_ref: str | None

        if checkout is not None:
            recipe_root = checkout.root
            manifest = load_manifest(recipe_root / MANIFEST_NAME)
            recipe_source = checkout.source.canonical
            recipe_revision = checkout.revision
            recipe_ref = checkout.tracking_ref or checkout.source.requested_ref
            recipe_tracking = checkout.tracking_ref is not None
        else:
            recipe_root, manifest = recipe(root)
            recipe_source = old_lock.recipe.source if old_lock.recipe else None
            recipe_revision = old_lock.recipe.revision if old_lock.recipe else None
            recipe_ref = old_lock.recipe.ref if old_lock.recipe else None
            recipe_tracking = old_lock.recipe.tracking if old_lock.recipe else False

        new_lock = resolve_lock(
            recipe_root,
            manifest,
            frozen=False,
            recipe_source=recipe_source,
            recipe_revision=recipe_revision,
            recipe_ref=recipe_ref,
            recipe_tracking=recipe_tracking,
        )
        new_lock = _select_component(namespace.component, old_lock, new_lock)
        values = parse_inputs(manifest, namespace.set)
        temporary_package, package = build_package(
            recipe_root, manifest, new_lock, values
        )

        try:
            service = UpdateService()
            preview = service.update(
                root,
                manifest,
                new_lock,
                package,
                inputs=values,
                checkout=checkout,
                dry_run=True,
            )

            if not namespace.dry_run:
                _confirm_update(namespace, root, old_lock, new_lock, manifest, preview)

            result = (
                preview
                if namespace.dry_run
                else service.update(
                    root,
                    manifest,
                    new_lock,
                    package,
                    inputs=values,
                    checkout=checkout,
                )
            )
        finally:
            temporary_package.cleanup()

    changes = _result_changes(result)
    emit(
        namespace,
        {
            "dryRun": namespace.dry_run,
            "changes": changes,
            "instanceId": result.state.instance_id if result.state else None,
        },
        ("Planned" if namespace.dry_run else "Updated")
        + f" {root} ({len(changes)} changes)",
    )
    return 0


def outdated(namespace: Any) -> int:
    root = _instance_root(namespace.dir)
    old_lock = load_lockfile(root / LOCKFILE_NAME)

    with tempfile.TemporaryDirectory(prefix="nesk-outdated-") as temporary:
        checkout = _updated_checkout(old_lock, Path(temporary) / "recipe")
        recipe_root = checkout.root if checkout else root
        manifest = load_manifest(recipe_root / MANIFEST_NAME)
        new_lock = resolve_lock(
            recipe_root,
            manifest,
            frozen=False,
            recipe_source=(checkout.source.canonical if checkout else None),
            recipe_revision=(checkout.revision if checkout else None),
            recipe_ref=(checkout.tracking_ref if checkout else None),
            recipe_tracking=bool(checkout and checkout.tracking_ref),
        )

    updates = _lock_changes(old_lock, new_lock)
    emit(
        namespace,
        {"outdated": updates, "count": len(updates)},
        "No updates available."
        if not updates
        else "Available updates:\n"
        + "\n".join(f"  {item['component']}: {item['from']} -> {item['to']}" for item in updates),
    )
    return 0


def diff(namespace: Any) -> int:
    root = _instance_root(namespace.dir)
    ledger = load_ownership(root)
    changes = []

    for relative, entry in ledger.files.items():
        if entry.digest is None:
            continue

        path = root / relative

        if not path.is_file() or path.is_symlink():
            changes.append({"path": relative, "status": "missing"})
            continue

        digest_value, _ = digest_file(path)

        if digest_value != entry.digest:
            changes.append({"path": relative, "status": "modified"})

    lockfile = load_lockfile(root / LOCKFILE_NAME)
    recipe_diff = []

    with tempfile.TemporaryDirectory(prefix="nesk-diff-") as temporary:
        checkout = _updated_checkout(lockfile, Path(temporary) / "recipe")

        if checkout is not None:
            recipe_diff = _recipe_diff(root, checkout)

    lines = [f"{item['status']:8} {item['path']}" for item in changes]
    lines.extend(recipe_diff)
    emit(
        namespace,
        {"managed": changes, "recipeDiff": recipe_diff},
        "No drift or recipe changes." if not lines else "\n".join(lines),
    )
    return 0


def recover(namespace: Any) -> int:
    root = _instance_root(namespace.dir)
    local_state = state_directory(root)
    journal = local_state / "transaction.json"
    backups = local_state / "backups"
    transaction_id = None

    if journal.is_file():
        try:
            transaction_id = json.loads(journal.read_text(encoding="utf-8"))["id"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise TransactionError("transaction journal is invalid") from exc

    if transaction_id is not None:
        backup = backups / transaction_id
    else:
        candidates = sorted(
            (path for path in backups.iterdir() if path.is_dir())
            if backups.exists()
            else (),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        if not candidates:
            raise TransactionError("no recoverable transaction was found")

        backup = candidates[0]

    if (backup / "install-plan.json").is_file():
        restore_install_backup(root, backup)

    restore_recipe_backup(root, backup)
    journal.unlink(missing_ok=True)
    emit(namespace, {"backup": str(backup)}, f"Recovered instance from {backup}")
    return 0


def _updated_checkout(lockfile: Lockfile, destination: Path) -> RecipeCheckout | None:
    recipe_lock = lockfile.recipe

    if recipe_lock is None or not recipe_lock.tracking:
        return None

    source = normalize_git_source(recipe_lock.source, recipe_lock.ref)
    return checkout_recipe(source, destination)


def _select_component(
    component: str | None,
    old: Lockfile,
    new: Lockfile,
) -> Lockfile:
    if component is None or component == "recipe":
        return new

    if component == "runtime":
        return Lockfile(
            manifest_digest=new.manifest_digest,
            target=new.target,
            sources=old.sources,
            runtime=new.runtime,
            build=old.build,
            recipe=new.recipe,
        )

    if component not in new.sources:
        raise ValidationError(f"unknown update component: {component}")

    sources = {**old.sources, component: new.sources[component]}
    return Lockfile(
        manifest_digest=new.manifest_digest,
        target=new.target,
        sources=sources,
        runtime=old.runtime,
        build=old.build,
        recipe=new.recipe,
    )


def _lock_changes(old: Lockfile, new: Lockfile) -> list[dict[str, str]]:
    changes = []

    if old.recipe and new.recipe and old.recipe.revision != new.recipe.revision:
        changes.append(
            {
                "component": "recipe",
                "from": old.recipe.revision,
                "to": new.recipe.revision,
            }
        )

    for source_id, source in new.sources.items():
        previous = old.sources.get(source_id)

        if previous is None or previous.digest != source.digest:
            changes.append(
                {
                    "component": source_id,
                    "from": previous.version if previous else "absent",
                    "to": source.version,
                }
            )

    if old.runtime.image != new.runtime.image:
        changes.append(
            {"component": "runtime", "from": old.runtime.image, "to": new.runtime.image}
        )

    return changes


def _result_changes(result: Any) -> list[dict[str, str]]:
    plans = [result.install_plan]

    if result.recipe_plan is not None:
        plans.append(result.recipe_plan)

    return [
        {"action": change.action, "path": change.path, "reason": change.reason}
        for plan in plans
        for change in plan.changes
        if change.action != "preserve"
    ]


def _recipe_diff(root: Path, checkout: RecipeCheckout) -> list[str]:
    lines: list[str] = []

    for relative in checkout.tracked_files:
        old = root / relative
        new = checkout.root / relative

        if old.is_file():
            try:
                old_lines = old.read_text(encoding="utf-8").splitlines()
                new_lines = new.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue

            lines.extend(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"current/{relative}",
                    tofile=f"incoming/{relative}",
                    lineterm="",
                )
            )
        else:
            lines.append(f"create   {relative}")

    return lines


def _confirm_update(
    namespace: Any,
    root: Path,
    old_lock: Lockfile,
    new_lock: Lockfile,
    manifest: Manifest,
    preview: Any,
) -> None:
    changes = _lock_changes(old_lock, new_lock)
    permission_summary = {
        "build": manifest.permissions.build,
        "network": bool(manifest.build and manifest.build.permissions.network),
        "runtimeImage": new_lock.runtime.image,
        "backup": list(manifest.update.backup),
    }

    if not namespace.json:
        print(f"Update target: {root}")
        print(f"Capabilities: {permission_summary}")

        for change in changes:
            print(f"  {change['component']}: {change['from']} -> {change['to']}")

    if namespace.yes:
        return

    if namespace.non_interactive or namespace.json:
        raise ConflictError("update requires --yes in non-interactive mode")

    if input("Apply this update? [y/N] ").strip().lower() not in {"y", "yes"}:
        raise ConflictError("update was not confirmed")
