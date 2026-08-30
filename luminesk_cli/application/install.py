"""Plan-first transactional package installation and update application."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from luminesk_cli.domain.errors import ConflictError, TransactionError, ValidationError
from luminesk_cli.domain.instance import (
    InstanceState,
    OwnershipEntry,
    OwnershipLedger,
    RecipeState,
    RuntimeState,
)
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, Lockfile, write_lockfile
from luminesk_cli.domain.manifest import Check, Manifest
from luminesk_cli.domain.package import PackageFile, ServerPackage
from luminesk_cli.domain.plan import Plan, PlanChange
from luminesk_cli.domain.primitives import safe_relative_path
from luminesk_cli.domain.recipe import RecipeSnapshot
from luminesk_cli.infrastructure.cache import digest_file
from luminesk_cli.infrastructure.package import extract_package
from luminesk_cli.infrastructure.recipe_snapshot import stage_recipe_snapshot
from luminesk_cli.infrastructure.state import (
    OWNERSHIP_FILE,
    RECIPE_DIRECTORY,
    STATE_FILE,
    InstanceIndex,
    atomic_write,
    canonical_json_bytes,
    load_ownership,
    load_state,
    state_directory,
    write_ownership,
    write_state,
)

ApplyHook = Callable[[str], None]


class TransactionalInstaller:
    def __init__(
        self,
        *,
        index: InstanceIndex | None = None,
        apply_hook: ApplyHook | None = None,
    ) -> None:
        self.index = index
        self.apply_hook = apply_hook

    def plan(self, package: ServerPackage, target: Path) -> Plan:
        root = target.resolve()
        ownership = load_ownership(root)
        changes = _plan_changes(package.metadata.files, root, ownership)
        return Plan(
            operation="update" if load_state(root) is not None else "install",
            target=str(root),
            changes=changes,
            requires_downtime=load_state(root) is not None,
        )

    def install(
        self,
        manifest: Manifest,
        lockfile: Lockfile,
        package: ServerPackage,
        target: Path,
        *,
        tag: str | None = None,
        inputs: Mapping[str, str | int | bool] | None = None,
        dry_run: bool = False,
        transaction_id: str | None = None,
        prune_backups: bool = True,
        recipe_snapshot: RecipeSnapshot | None = None,
    ) -> tuple[Plan, InstanceState | None]:
        root = target.resolve()
        _validate_package_binding(manifest, lockfile, package)
        old_state = load_state(root)

        if old_state is not None and old_state.pending_transaction is not None:
            raise TransactionError(
                "instance has an unfinished transaction; recover it first",
                transaction=old_state.pending_transaction,
            )

        plan = self.plan(package, root)

        if plan.has_conflicts:
            conflicts = [
                change.path for change in plan.changes if change.action == "conflict"
            ]
            raise ConflictError(
                "install plan contains user-file conflicts", conflicts=conflicts
            )

        if dry_run:
            return plan, old_state

        transaction_id = transaction_id or uuid.uuid4().hex
        local_state = state_directory(root)
        staging = local_state / "staging" / transaction_id
        payload = staging / "payload"
        backup = local_state / "backups" / transaction_id
        journal = local_state / "transaction.json"

        if journal.exists():
            raise TransactionError(
                "instance has an unfinished transaction journal; recover it first"
            )

        extract_package(package, payload)
        if recipe_snapshot is not None:
            stage_recipe_snapshot(recipe_snapshot, staging / RECIPE_DIRECTORY)
        old_ownership = load_ownership(root)
        _backup_transaction_files(root, backup, plan, manifest)
        _backup_metadata(root, backup)
        _backup_recipe_snapshot(root, backup, recipe_snapshot is not None)
        now = datetime.now(UTC).isoformat()
        pending_state = _new_state(
            manifest,
            lockfile,
            package,
            root,
            tag=tag,
            old_state=old_state,
            inputs=inputs or {},
            now=now,
            pending_transaction=transaction_id,
        )
        atomic_write(
            journal,
            canonical_json_bytes(
                {
                    "transactionVersion": 1,
                    "id": transaction_id,
                    "operation": plan.operation,
                    "target": str(root),
                    "packageDigest": package.digest,
                    "phase": "pending",
                    "changes": [
                        {"action": change.action, "path": change.path}
                        for change in plan.changes
                    ],
                }
            ),
        )
        write_state(root, pending_state)

        try:
            _apply_plan(root, payload, plan, package.metadata.files, self.apply_hook)
            if recipe_snapshot is not None:
                _install_recipe_snapshot(root, staging, recipe_snapshot)
            _run_post_install_checks(root, manifest.checks)
            new_ownership = _create_ownership(package.metadata.files, root)
            write_lockfile(root / LOCKFILE_NAME, lockfile)
            write_ownership(root, new_ownership)
            committed_state = replace(pending_state, pending_transaction=None)
            write_state(root, committed_state)
            journal.unlink()
            shutil.rmtree(staging)
        except BaseException as exc:
            try:
                _rollback(root, backup, plan, old_state, old_ownership)
                journal.unlink(missing_ok=True)
            except BaseException as rollback_exc:
                raise TransactionError(
                    "install failed and rollback was incomplete",
                    original=str(exc),
                    rollback=str(rollback_exc),
                    transaction=transaction_id,
                ) from exc

            raise TransactionError(
                f"install failed and was rolled back: {exc}",
                transaction=transaction_id,
            ) from exc

        if prune_backups:
            prune_instance_backups(root, manifest.update.retain_backups)

        if self.index is not None:
            self.index.register(committed_state)

        return plan, committed_state


def _validate_package_binding(
    manifest: Manifest,
    lockfile: Lockfile,
    package: ServerPackage,
) -> None:
    if lockfile.manifest_digest != manifest.digest:
        raise ValidationError("lockfile does not match manifest")

    if package.metadata.manifest_digest != manifest.digest:
        raise ValidationError("package does not match manifest")

    if package.metadata.lock_digest != lockfile.digest:
        raise ValidationError("package does not match lockfile")

    if package.metadata.target != lockfile.target:
        raise ValidationError("package target does not match lockfile")


def _plan_changes(
    files: tuple[PackageFile, ...],
    root: Path,
    ownership: OwnershipLedger,
) -> tuple[PlanChange, ...]:
    changes = []
    new_paths = {item.path for item in files}

    for item in files:
        target = root / item.path

        if item.type == "directory":
            if not target.exists():
                action = "create"
                reason = "declared package directory is absent"
            elif target.is_dir() and not target.is_symlink():
                action = "preserve"
                reason = "existing directory is retained"
            else:
                action = "conflict"
                reason = "a non-directory occupies the declared directory path"

            changes.append(PlanChange(action, item.path, reason))  # type: ignore[arg-type]
            continue

        if not target.exists() and not target.is_symlink():
            changes.append(
                PlanChange("create", item.path, "managed file is absent", item.digest)
            )
            continue

        if not target.is_file() or target.is_symlink():
            changes.append(
                PlanChange("conflict", item.path, "target is not a regular file")
            )
            continue

        current_digest, _ = digest_file(target)

        if current_digest == item.digest:
            changes.append(
                PlanChange(
                    "preserve",
                    item.path,
                    "installed content already matches",
                    current_digest,
                )
            )
            continue

        if item.ownership in {"preserve", "data"}:
            changes.append(
                PlanChange(
                    "preserve",
                    item.path,
                    "user-preserved content is not overwritten",
                    current_digest,
                )
            )
            continue

        old_entry = ownership.files.get(item.path)

        if old_entry is not None and old_entry.digest == current_digest:
            changes.append(
                PlanChange(
                    "replace",
                    item.path,
                    "unchanged managed file has a new package version",
                    item.digest,
                )
            )
        else:
            changes.append(
                PlanChange(
                    "conflict",
                    item.path,
                    "managed file was modified outside Nesk",
                    current_digest,
                )
            )

    for path, entry in ownership.files.items():
        if path in new_paths or entry.mode not in {"managed", "generated"}:
            continue

        target = root / path

        if not target.exists():
            continue

        if target.is_file() and not target.is_symlink():
            current_digest, _ = digest_file(target)

            if current_digest == entry.digest:
                changes.append(
                    PlanChange("remove", path, "managed file left the package")
                )
                continue

        changes.append(
            PlanChange("conflict", path, "removed package file has local changes")
        )

    return tuple(changes)


def _apply_plan(
    root: Path,
    payload: Path,
    plan: Plan,
    files: tuple[PackageFile, ...],
    hook: ApplyHook | None,
) -> None:
    metadata = {item.path: item for item in files}

    for change in plan.changes:
        target = root / change.path

        if change.action == "create" and metadata[change.path].type == "directory":
            target.mkdir(parents=True, exist_ok=True)
        elif change.action in {"create", "replace"}:
            source = payload / change.path
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, target)
            target.chmod(metadata[change.path].mode)
        elif change.action == "remove":
            target.unlink(missing_ok=True)

        if hook is not None and change.action not in {"preserve", "conflict"}:
            hook(change.path)


def _run_post_install_checks(root: Path, checks: tuple[Check, ...]) -> None:
    for check in checks:
        if check.phase != "post-install" or check.kind != "file":
            continue

        assert check.path is not None
        target = root / check.path

        if check.required and (not target.is_file() or target.is_symlink()):
            raise TransactionError(
                f"required post-install check failed: {check.id}",
                path=check.path,
            )


def _backup_transaction_files(
    root: Path,
    backup: Path,
    plan: Plan,
    manifest: Manifest,
) -> None:
    backup.mkdir(parents=True, exist_ok=True)
    atomic_write(
        backup / "install-plan.json",
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
    paths = {
        change.path for change in plan.changes if change.action in {"replace", "remove"}
    }
    paths.update(manifest.update.backup)

    for relative in sorted(paths):
        source = root / relative

        if not source.exists() or source.is_symlink():
            continue

        destination = backup / "payload" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(source, destination, symlinks=False)
        elif source.is_file():
            shutil.copy2(source, destination)


def _backup_metadata(root: Path, backup: Path) -> None:
    for source in (
        root / LOCKFILE_NAME,
        state_directory(root) / STATE_FILE,
        state_directory(root) / OWNERSHIP_FILE,
    ):
        if source.is_file():
            destination = backup / "metadata" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _backup_recipe_snapshot(root: Path, backup: Path, enabled: bool) -> None:
    if not enabled:
        return
    root_manifest = root / "luminesk.toml"
    canonical = state_directory(root) / RECIPE_DIRECTORY
    if root_manifest.exists() and (
        not root_manifest.is_file() or root_manifest.is_symlink()
    ):
        raise TransactionError("installed luminesk.toml path is unsafe")
    if canonical.exists() and (not canonical.is_dir() or canonical.is_symlink()):
        raise TransactionError("canonical recipe snapshot path is unsafe")
    atomic_write(
        backup / "recipe-state.json",
        canonical_json_bytes(
            {
                "rootManifest": root_manifest.is_file(),
                "canonicalSnapshot": canonical.is_dir(),
            }
        ),
    )
    if root_manifest.is_file():
        shutil.copy2(root_manifest, backup / "root-luminesk.toml")
    if canonical.is_dir():
        shutil.copytree(canonical, backup / "recipe-snapshot")


def _install_recipe_snapshot(
    root: Path,
    staging: Path,
    snapshot: RecipeSnapshot,
) -> None:
    canonical = state_directory(root) / RECIPE_DIRECTORY
    staged = staging / RECIPE_DIRECTORY
    if canonical.exists():
        if not canonical.is_dir() or canonical.is_symlink():
            raise TransactionError("canonical recipe snapshot path is unsafe")
        shutil.rmtree(canonical)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, canonical)
    manifest_source = canonical / "luminesk.toml"
    digest, _ = digest_file(manifest_source)
    if digest != snapshot.origin.manifest_digest:
        raise TransactionError("staged recipe manifest digest changed")
    atomic_write(root / "luminesk.toml", manifest_source.read_bytes())


def _rollback(
    root: Path,
    backup: Path,
    plan: Plan,
    old_state: InstanceState | None,
    old_ownership: OwnershipLedger,
) -> None:
    for change in reversed(plan.changes):
        target = root / change.path
        saved = backup / "payload" / change.path

        if saved.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)

            target.parent.mkdir(parents=True, exist_ok=True)

            if saved.is_dir():
                shutil.copytree(saved, target)
            else:
                shutil.copy2(saved, target)
        elif change.action == "create":
            if target.is_dir():
                try:
                    target.rmdir()
                except OSError:
                    pass
            else:
                target.unlink(missing_ok=True)

    lock_backup = backup / "metadata" / LOCKFILE_NAME

    if lock_backup.is_file():
        shutil.copy2(lock_backup, root / LOCKFILE_NAME)
    else:
        (root / LOCKFILE_NAME).unlink(missing_ok=True)

    if old_state is None:
        (state_directory(root) / STATE_FILE).unlink(missing_ok=True)
        (state_directory(root) / OWNERSHIP_FILE).unlink(missing_ok=True)
    else:
        write_state(root, old_state)
        write_ownership(root, old_ownership)

    _restore_recipe_snapshot(root, backup)


def _restore_recipe_snapshot(root: Path, backup: Path) -> None:
    state_path = backup / "recipe-state.json"
    if not state_path.is_file():
        return
    try:
        value = json.loads(state_path.read_text(encoding="utf-8"))
        had_manifest = value["rootManifest"]
        had_snapshot = value["canonicalSnapshot"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise TransactionError("recipe snapshot backup state is invalid") from exc
    if not isinstance(had_manifest, bool) or not isinstance(had_snapshot, bool):
        raise TransactionError("recipe snapshot backup state is invalid")

    root_manifest = root / "luminesk.toml"
    if had_manifest:
        shutil.copy2(backup / "root-luminesk.toml", root_manifest)
    else:
        root_manifest.unlink(missing_ok=True)

    canonical = state_directory(root) / RECIPE_DIRECTORY
    if canonical.exists():
        if canonical.is_dir() and not canonical.is_symlink():
            shutil.rmtree(canonical)
        else:
            canonical.unlink()
    if had_snapshot:
        shutil.copytree(backup / "recipe-snapshot", canonical)


def _create_ownership(files: tuple[PackageFile, ...], root: Path) -> OwnershipLedger:
    entries = {}

    for item in files:
        target = root / item.path
        digest = None

        if item.type == "file" and target.is_file():
            digest, _ = digest_file(target)

        entries[item.path] = OwnershipEntry(mode=item.ownership, digest=digest)

    return OwnershipLedger(files=entries)


def _new_state(
    manifest: Manifest,
    lockfile: Lockfile,
    package: ServerPackage,
    root: Path,
    *,
    tag: str | None,
    old_state: InstanceState | None,
    inputs: Mapping[str, str | int | bool],
    now: str,
    pending_transaction: str,
) -> InstanceState:
    return InstanceState(
        instance_id=(old_state.instance_id if old_state else str(uuid.uuid4())),
        name=manifest.package.name,
        tag=tag or (old_state.tag if old_state else manifest.package.name),
        root=str(root),
        applied_lock_digest=lockfile.digest,
        installed_package_digest=package.digest,
        recipe=RecipeState(
            source=lockfile.recipe.source if lockfile.recipe else None,
            revision=lockfile.recipe.revision if lockfile.recipe else None,
        ),
        inputs=_persisted_inputs(manifest, inputs),
        runtime=old_state.runtime if old_state else RuntimeState(),
        created_at=old_state.created_at if old_state else now,
        updated_at=now,
        last_readiness_at=(old_state.last_readiness_at if old_state else None),
        pending_transaction=pending_transaction,
    )


def prune_instance_backups(root: Path, retain: int) -> None:
    directory = state_directory(root) / "backups"

    if not directory.exists():
        return

    backups = sorted(
        (path for path in directory.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[retain:]:
        shutil.rmtree(old_backup)


def restore_install_backup(root: Path, backup: Path) -> None:
    plan_path = backup / "install-plan.json"

    if not plan_path.is_file():
        raise TransactionError("backup has no install plan", backup=str(backup))

    try:
        raw_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        raw_changes = raw_plan["changes"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise TransactionError("backup install plan is invalid") from exc

    if not isinstance(raw_changes, list):
        raise TransactionError("backup install changes must be an array")

    for raw_change in reversed(raw_changes):
        if not isinstance(raw_change, dict):
            raise TransactionError("backup install change is invalid")

        action = raw_change.get("action")
        relative = raw_change.get("path")

        if not isinstance(action, str) or not isinstance(relative, str):
            raise TransactionError("backup install change is invalid")

        safe_path = safe_relative_path(relative, "install.backup.path")
        target = root / safe_path
        saved = backup / "payload" / safe_path

        if saved.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)

            target.parent.mkdir(parents=True, exist_ok=True)

            if saved.is_dir():
                shutil.copytree(saved, target)
            else:
                shutil.copy2(saved, target)
        elif action == "create":
            if target.is_dir():
                try:
                    target.rmdir()
                except OSError:
                    pass
            else:
                target.unlink(missing_ok=True)

    metadata = backup / "metadata"

    for name, destination in (
        (LOCKFILE_NAME, root / LOCKFILE_NAME),
        (STATE_FILE, state_directory(root) / STATE_FILE),
        (OWNERSHIP_FILE, state_directory(root) / OWNERSHIP_FILE),
    ):
        saved = metadata / name

        if saved.is_file():
            atomic_write(destination, saved.read_bytes())
        else:
            destination.unlink(missing_ok=True)

    _restore_recipe_snapshot(root, backup)


def _persisted_inputs(
    manifest: Manifest,
    values: Mapping[str, str | int | bool],
) -> dict[str, str | int | bool]:
    result = {}

    for spec in manifest.inputs:
        if spec.secret:
            continue

        value = values.get(spec.name)

        if value is None:
            value = spec.default

        if value is not None:
            result[spec.name] = value

    return result
