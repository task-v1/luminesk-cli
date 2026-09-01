from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from luminesk_cli.application.install import TransactionalInstaller
from luminesk_cli.cli.commands.common import (
    build_package,
    cache,
    catalog_store,
    emit,
    index_path,
    parse_inputs,
    recipe,
    recipe_cache,
    resolve_lock,
    validate_frozen_lock,
)
from luminesk_cli.domain.errors import ConflictError, ValidationError
from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.primitives import PACKAGE_NAME_RE
from luminesk_cli.domain.recipe import RecipeSnapshot
from luminesk_cli.infrastructure.catalog import CatalogClient
from luminesk_cli.infrastructure.platform import current_platform
from luminesk_cli.infrastructure.recipe import (
    acquire_github_recipe,
    ensure_empty_target,
    normalize_git_source,
)
from luminesk_cli.infrastructure.recipe_cache import database_locator, github_locator
from luminesk_cli.infrastructure.recipe_snapshot import create_recipe_snapshot
from luminesk_cli.infrastructure.state import InstanceIndex


def run(namespace: Any) -> int:
    target = Path(namespace.dir or ".").expanduser().resolve()
    if namespace.source is None:
        root, manifest = recipe(target)
        return _install_snapshot(
            namespace,
            create_recipe_snapshot(root, manifest),
            target,
            confirm=False,
        )

    raw_source = namespace.source.strip()
    source_path = Path(raw_source).expanduser()
    if source_path.exists():
        if namespace.ref is not None:
            raise ValidationError("--ref is valid only for direct GitHub recipes")
        recipe_root = source_path.resolve()
        root, manifest = recipe(recipe_root)
        if recipe_root != target:
            ensure_empty_target(target)
        return _install_snapshot(
            namespace,
            create_recipe_snapshot(root, manifest),
            target,
            confirm=recipe_root != target,
        )
    if _looks_like_local_path(raw_source):
        raise ValidationError(f"local recipe path does not exist: {raw_source}")

    database_name = _database_name(raw_source)
    if database_name is not None:
        if namespace.ref is not None:
            raise ValidationError("--ref is valid only for direct GitHub recipes")
        ensure_empty_target(target)
        catalog = catalog_store().load_active()
        entry = next(
            (
                candidate
                for candidate in catalog.entries
                if candidate.name == database_name
            ),
            None,
        )
        if entry is None:
            raise ValidationError(f"catalog recipe not found: {database_name}")
        locator = database_locator(catalog.revision, entry.name)
        if namespace.frozen:
            cached = recipe_cache().load_locator(locator, current_platform())
            return _install_snapshot(
                namespace,
                cached.snapshot,
                target,
                confirm=True,
                cached_lock=cached.lockfile,
            )
        with tempfile.TemporaryDirectory(
            prefix="luminesk-database-recipe-"
        ) as temporary:
            snapshot = CatalogClient(catalog_store()).acquire_entry(
                catalog,
                entry,
                Path(temporary) / "recipe",
            )
            return _install_snapshot(
                namespace,
                snapshot,
                target,
                confirm=True,
                cache_locator=locator,
            )

    ensure_empty_target(target)
    source = normalize_git_source(raw_source, namespace.ref)
    locator = github_locator(source.canonical, source.requested_ref)
    if namespace.frozen:
        cached = recipe_cache().load_locator(locator, current_platform())
        return _install_snapshot(
            namespace,
            cached.snapshot,
            target,
            confirm=True,
            cached_lock=cached.lockfile,
        )
    with tempfile.TemporaryDirectory(prefix="luminesk-github-recipe-") as temporary:
        snapshot = acquire_github_recipe(
            source,
            Path(temporary) / "recipe",
            cache(),
        )
        return _install_snapshot(
            namespace,
            snapshot,
            target,
            confirm=True,
            cache_locator=locator,
        )


def _database_name(source: str) -> str | None:
    explicit = source.startswith("db:")
    name = source.removeprefix("db:") if explicit else source
    if not explicit and (
        "/" in source or source.startswith("github:") or source.startswith("https://")
    ):
        return None
    if PACKAGE_NAME_RE.fullmatch(name) is None:
        raise ValidationError(
            "database recipe name must be a lowercase ASCII identifier"
        )
    return name


def _looks_like_local_path(source: str) -> bool:
    return source.startswith((".", "~", "/")) or "\\" in source


def _install_snapshot(
    namespace: Any,
    snapshot: RecipeSnapshot,
    target: Path,
    *,
    confirm: bool,
    cached_lock: Lockfile | None = None,
    cache_locator: str | None = None,
) -> int:
    root = snapshot.root
    manifest = snapshot.manifest
    origin = snapshot.origin
    lockfile = (
        validate_frozen_lock(
            cached_lock,
            manifest,
            cache(),
            recipe_origin=origin,
        )
        if cached_lock is not None
        else resolve_lock(
            root,
            manifest,
            frozen=namespace.frozen,
            recipe_origin=origin,
        )
    )
    values = parse_inputs(manifest, namespace.set, namespace.set_file)
    temporary, package = build_package(root, manifest, lockfile, values)

    try:
        if origin.kind != "local" and cached_lock is None:
            recipe_cache().store(snapshot, lockfile, locator=cache_locator)
        installer = TransactionalInstaller(index=InstanceIndex(index_path()))
        plan = installer.plan(package, target)
        if plan.has_conflicts:
            conflicts = [
                change.path for change in plan.changes if change.action == "conflict"
            ]
            raise ConflictError(
                "install plan contains user-file conflicts", conflicts=conflicts
            )
        if confirm:
            _confirm(namespace, snapshot, target, lockfile)
        if namespace.dry_run:
            return _emit_result(namespace, plan, None)
        plan, state = installer.install(
            manifest,
            lockfile,
            package,
            target,
            inputs=values,
            recipe_snapshot=snapshot,
        )
        return _emit_result(namespace, plan, state)
    finally:
        temporary.cleanup()


def _confirm(
    namespace: Any,
    snapshot: RecipeSnapshot,
    target: Path,
    lockfile: Lockfile,
) -> None:
    manifest = snapshot.manifest
    origin = snapshot.origin
    trust = {
        "database": "official",
        "github": "direct",
        "local": "local",
    }[origin.kind]
    source_types = ", ".join(source.type for source in manifest.sources) or "none"
    artifacts = (
        ", ".join(
            f"{source_id}@{resolved.version} ({resolved.digest})"
            for source_id, resolved in sorted(lockfile.sources.items())
        )
        or "none"
    )
    template_files = sum(
        1
        for entry in snapshot.entries
        if entry.type == "file"
        and manifest.template is not None
        and (
            entry.path == manifest.template
            or entry.path.startswith(f"{manifest.template}/")
        )
    )
    summary = (
        f"Recipe origin: {trust} ({origin.source})\n"
        f"Exact recipe revision: {origin.revision}\n"
        f"Recipe version: {origin.version}\n"
        f"Source types: {source_types}\n"
        f"Resolved artifacts: {artifacts}\n"
        f"Runtime image: {lockfile.runtime.image}\n"
        f"Build: {'enabled' if lockfile.build is not None else 'disabled'}\n"
        f"Build network: "
        f"{'enabled' if manifest.build is not None and manifest.build.network else 'disabled'}\n"
        f"Template files: {template_files}\n"
        f"Writes: {target}"
    )
    if not namespace.json:
        print(summary)
    if namespace.yes:
        return
    if namespace.non_interactive or namespace.json:
        raise ConflictError("install requires --yes in non-interactive mode")
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
