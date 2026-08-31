"""Shared helpers loaded only after a 2.0 command is selected."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir, user_config_dir

from luminesk_cli.application.locking import LockService
from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, Lockfile, load_lockfile
from luminesk_cli.domain.manifest import MANIFEST_NAME, Manifest, load_manifest
from luminesk_cli.domain.package import ServerPackage
from luminesk_cli.domain.recipe import RecipeOrigin
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.catalog import CatalogStore
from luminesk_cli.infrastructure.platform import current_platform
from luminesk_cli.infrastructure.recipe_cache import RecipeCache

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def cache() -> ContentCache:
    return ContentCache(Path(user_cache_dir("luminesk_cli")) / "v2")


def index_path() -> Path:
    return Path(user_config_dir("luminesk_cli")) / "state.sqlite3"


def catalog_store() -> CatalogStore:
    return CatalogStore(Path(user_cache_dir("luminesk_cli")) / "v2" / "catalog")


def recipe_cache() -> RecipeCache:
    return RecipeCache(Path(user_cache_dir("luminesk_cli")) / "v2" / "recipes")


def recipe(directory: str | Path) -> tuple[Path, Manifest]:
    root = Path(directory).expanduser().resolve()
    return root, load_manifest(root / MANIFEST_NAME)


def validate_frozen_lock(
    lockfile: Lockfile,
    manifest: Manifest,
    content_cache: ContentCache,
    *,
    recipe_origin: RecipeOrigin | None = None,
) -> Lockfile:
    if lockfile.manifest_digest != manifest.digest:
        raise ValidationError("frozen lockfile does not match luminesk.toml")

    if lockfile.target != current_platform():
        raise ValidationError(
            f"frozen lock target {lockfile.target} does not match {current_platform()}"
        )

    for source_id, source in lockfile.sources.items():
        if content_cache.restore(source.digest) is None:
            raise ValidationError(
                f"frozen source {source_id} is absent from content cache"
            )

    if recipe_origin is not None:
        recipe_lock = lockfile.recipe
        if recipe_lock is None or (
            recipe_lock.kind,
            recipe_lock.source,
            recipe_lock.revision,
            recipe_lock.ref,
            recipe_lock.tracking,
            recipe_lock.entry,
            recipe_lock.path,
            recipe_lock.version,
            recipe_lock.manifest_digest,
            recipe_lock.template_digest,
        ) != (
            recipe_origin.kind,
            recipe_origin.source,
            recipe_origin.revision,
            recipe_origin.ref,
            recipe_origin.tracking,
            recipe_origin.entry,
            recipe_origin.path,
            recipe_origin.version,
            recipe_origin.manifest_digest,
            recipe_origin.template_digest,
        ):
            raise ValidationError("frozen lockfile does not match recipe origin")

    return lockfile


def frozen_lock(
    root: Path,
    manifest: Manifest,
    content_cache: ContentCache,
    *,
    recipe_origin: RecipeOrigin | None = None,
) -> Lockfile:
    return validate_frozen_lock(
        load_lockfile(root / LOCKFILE_NAME),
        manifest,
        content_cache,
        recipe_origin=recipe_origin,
    )


def resolve_lock(
    root: Path,
    manifest: Manifest,
    *,
    frozen: bool,
    recipe_origin: RecipeOrigin | None = None,
) -> Lockfile:
    content_cache = cache()

    if frozen:
        return frozen_lock(
            root,
            manifest,
            content_cache,
            recipe_origin=recipe_origin,
        )

    return LockService(content_cache).create(
        manifest,
        root,
        recipe_origin=recipe_origin,
    )


def build_package(
    root: Path,
    manifest: Manifest,
    lockfile: Lockfile,
    values: dict[str, str | int | bool],
) -> tuple[tempfile.TemporaryDirectory[str], ServerPackage]:
    temporary = tempfile.TemporaryDirectory(prefix="luminesk-cli-package-")
    package = DeclarativeBuilder(cache()).build(
        manifest,
        lockfile,
        root,
        Path(temporary.name) / f"{manifest.package.name}.lumineskpkg",
        inputs=values,
    )
    return temporary, package


def parse_inputs(
    manifest: Manifest,
    arguments: list[str],
) -> dict[str, str | int | bool]:
    specs = {item.name: item for item in manifest.inputs}
    values: dict[str, str | int | bool] = {}

    for argument in arguments:
        if "=" not in argument:
            raise ValidationError(f"input override must be KEY=VALUE: {argument}")

        name, raw_value = argument.split("=", 1)
        spec = specs.get(name)

        if spec is None:
            raise ValidationError(f"unknown input: {name}")

        if spec.type == "integer":
            try:
                value: str | int | bool = int(raw_value)
            except ValueError as exc:
                raise ValidationError(f"input {name} must be an integer") from exc
        elif spec.type == "boolean":
            normalized = raw_value.lower()

            if normalized not in {"true", "false"}:
                raise ValidationError(f"input {name} must be true or false")

            value = normalized == "true"
        else:
            value = raw_value

        values[name] = value

    return values


def sanitize(value: str) -> str:
    return CONTROL_CHARACTERS.sub("�", value).replace("\x1b", "�")


def emit(namespace: Any, payload: dict[str, Any], plain: str) -> None:
    if bool(getattr(namespace, "json", False)):
        print(json.dumps({"ok": True, **payload}, ensure_ascii=False, sort_keys=True))
    else:
        print(sanitize(plain))
