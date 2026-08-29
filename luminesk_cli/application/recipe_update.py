"""Transactional application of tracked recipe trees with drift detection."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from luminesk_cli.domain.errors import ConflictError, TransactionError
from luminesk_cli.domain.instance import OwnershipEntry, OwnershipLedger
from luminesk_cli.domain.plan import Plan, PlanChange
from luminesk_cli.domain.primitives import safe_relative_path
from luminesk_cli.infrastructure.cache import digest_file
from luminesk_cli.infrastructure.recipe import RecipeCheckout
from luminesk_cli.infrastructure.state import (
    RECIPE_OWNERSHIP_FILE,
    atomic_write,
    canonical_json_bytes,
    load_recipe_ownership,
    state_directory,
    write_recipe_ownership,
)


def record_recipe_ownership(
    checkout: RecipeCheckout,
    target: Path,
) -> OwnershipLedger:
    entries = {}

    for relative in checkout.tracked_files:
        path = target / relative
        digest, _ = digest_file(path)
        entries[relative] = OwnershipEntry(mode="managed", digest=digest)

    ledger = OwnershipLedger(entries)
    write_recipe_ownership(target, ledger)
    return ledger


class RecipeUpdater:
    def plan(self, checkout: RecipeCheckout, target: Path) -> Plan:
        root = target.resolve()
        ledger = load_recipe_ownership(root)
        changes = []
        incoming = set(checkout.tracked_files)

        for relative in checkout.tracked_files:
            source = checkout.root / relative
            destination = root / relative
            incoming_digest, _ = digest_file(source)

            if not destination.exists():
                changes.append(
                    PlanChange("create", relative, "new tracked recipe file", incoming_digest)
                )
                continue

            if not destination.is_file() or destination.is_symlink():
                changes.append(
                    PlanChange("conflict", relative, "recipe target is not a regular file")
                )
                continue

            current_digest, _ = digest_file(destination)

            if current_digest == incoming_digest:
                changes.append(
                    PlanChange("preserve", relative, "recipe file already matches")
                )
                continue

            old = ledger.files.get(relative)

            if old is not None and old.digest == current_digest:
                changes.append(
                    PlanChange("replace", relative, "tracked recipe file changed upstream")
                )
            else:
                changes.append(
                    PlanChange("conflict", relative, "tracked recipe file has local changes")
                )

        for relative, entry in ledger.files.items():
            if relative in incoming:
                continue

            destination = root / relative

            if not destination.exists():
                continue

            if destination.is_file() and not destination.is_symlink():
                digest, _ = digest_file(destination)

                if digest == entry.digest:
                    changes.append(
                        PlanChange("remove", relative, "file removed from recipe")
                    )
                    continue

            changes.append(
                PlanChange("conflict", relative, "removed recipe file has local changes")
            )

        return Plan(operation="update", target=str(root), changes=tuple(changes))

    def apply(
        self,
        checkout: RecipeCheckout,
        target: Path,
        backup: Path,
    ) -> Plan:
        root = target.resolve()
        plan = self.plan(checkout, root)

        if plan.has_conflicts:
            raise ConflictError(
                "recipe update contains local-file conflicts",
                conflicts=[
                    change.path
                    for change in plan.changes
                    if change.action == "conflict"
                ],
            )

        backup.mkdir(parents=True, exist_ok=True)
        atomic_write(
            backup / "recipe-plan.json",
            canonical_json_bytes(
                {
                    "planVersion": 1,
                    "changes": [
                        {"action": change.action, "path": change.path}
                        for change in plan.changes
                    ],
                }
            ),
        )
        ledger_path = state_directory(root) / RECIPE_OWNERSHIP_FILE

        if ledger_path.is_file():
            shutil.copy2(ledger_path, backup / RECIPE_OWNERSHIP_FILE)

        for change in plan.changes:
            destination = root / change.path

            if change.action in {"replace", "remove"}:
                saved = backup / "payload" / change.path
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, saved)

        try:
            for change in plan.changes:
                destination = root / change.path

                if change.action in {"create", "replace"}:
                    source = checkout.root / change.path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    descriptor, temporary_name = tempfile.mkstemp(
                        dir=destination.parent,
                        prefix=f".{destination.name}.",
                        suffix=".tmp",
                    )
                    os.close(descriptor)
                    temporary = Path(temporary_name)

                    try:
                        shutil.copy2(source, temporary)
                        os.replace(temporary, destination)
                    finally:
                        temporary.unlink(missing_ok=True)
                elif change.action == "remove":
                    destination.unlink()

            record_recipe_ownership(checkout, root)
            return plan
        except BaseException as exc:
            try:
                restore_recipe_backup(root, backup)
            except BaseException as rollback_exc:
                raise TransactionError(
                    "recipe update failed and rollback was incomplete",
                    original=str(exc),
                    rollback=str(rollback_exc),
                ) from exc

            raise TransactionError(
                f"recipe update failed and was rolled back: {exc}"
            ) from exc


def restore_recipe_backup(root: Path, backup: Path) -> None:
    plan_path = backup / "recipe-plan.json"

    if not plan_path.is_file():
        return

    try:
        raw = json.loads(plan_path.read_text(encoding="utf-8"))
        changes = raw["changes"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise TransactionError("recipe backup plan is invalid") from exc

    if not isinstance(changes, list):
        raise TransactionError("recipe backup changes must be an array")

    for raw_change in reversed(changes):
        if not isinstance(raw_change, dict):
            raise TransactionError("recipe backup change is invalid")

        action = raw_change.get("action")
        raw_path = raw_change.get("path")

        if not isinstance(action, str) or not isinstance(raw_path, str):
            raise TransactionError("recipe backup change is invalid")

        relative = safe_relative_path(raw_path, "recipe.backup.path")
        destination = root / relative
        saved = backup / "payload" / relative

        if saved.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(saved, destination)
        elif action == "create":
            destination.unlink(missing_ok=True)

    ledger_backup = backup / RECIPE_OWNERSHIP_FILE
    ledger_path = state_directory(root) / RECIPE_OWNERSHIP_FILE

    if ledger_backup.is_file():
        atomic_write(ledger_path, ledger_backup.read_bytes())
    else:
        ledger_path.unlink(missing_ok=True)
