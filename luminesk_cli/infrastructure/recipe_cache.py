"""Verified immutable cache generations for exact recipe snapshots and locks."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.domain.lockfile import (
    LOCKFILE_NAME,
    Lockfile,
    RecipeLock,
    load_lockfile,
    write_lockfile,
)
from luminesk_cli.domain.manifest import MANIFEST_NAME, load_manifest
from luminesk_cli.domain.primitives import (
    require_array,
    require_int,
    require_keys,
    require_string,
    require_table,
    safe_relative_path,
    sha256_digest,
    validate_digest,
)
from luminesk_cli.domain.recipe import RecipeOrigin, RecipeSnapshot, RecipeSnapshotEntry
from luminesk_cli.infrastructure.recipe_snapshot import (
    create_recipe_snapshot,
    full_recipe_context_entries,
    stage_recipe_snapshot,
)
from luminesk_cli.infrastructure.state import atomic_write, canonical_json_bytes

RECIPE_CACHE_VERSION = 1
METADATA_FILE = "snapshot.json"


@dataclass(slots=True, frozen=True)
class CachedRecipe:
    snapshot: RecipeSnapshot
    lockfile: Lockfile


class RecipeCache:
    def __init__(self, root: Path) -> None:
        self.root = root

    def store(
        self,
        snapshot: RecipeSnapshot,
        lockfile: Lockfile,
        *,
        locator: str | None = None,
    ) -> CachedRecipe:
        _validate_binding(snapshot.origin, lockfile)
        staged_entries = (
            full_recipe_context_entries(snapshot.root)
            if snapshot.manifest.build is not None
            else snapshot.entries
        )
        generation = _generation_key(snapshot.origin, lockfile)
        destination = self.root / "snapshots" / generation
        staging_parent = self.root / ".staging"
        staging_parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="recipe-", dir=staging_parent))
        cached_snapshot = RecipeSnapshot(
            root=snapshot.root,
            manifest=snapshot.manifest,
            origin=snapshot.origin,
            entries=staged_entries,
        )
        try:
            stage_recipe_snapshot(cached_snapshot, staging / "recipe")
            cached_entries = full_recipe_context_entries(staging / "recipe")
            write_lockfile(staging / LOCKFILE_NAME, lockfile)
            atomic_write(
                staging / METADATA_FILE,
                canonical_json_bytes(
                    {
                        "cacheVersion": RECIPE_CACHE_VERSION,
                        "generation": generation,
                        "lockDigest": lockfile.digest,
                        "files": [_entry_dict(entry) for entry in cached_entries],
                    }
                ),
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                existing = self._load_generation(generation)
                if existing.lockfile.to_bytes() != lockfile.to_bytes():
                    raise SecurityError("immutable recipe cache generation collision")
            else:
                os.replace(staging, destination)
            self._point(_origin_locator(snapshot.origin), lockfile.target, generation)
            if locator is not None:
                self._point(locator, lockfile.target, generation)
            return self._load_generation(generation)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def load_exact(
        self,
        origin: RecipeOrigin,
        lockfile: Lockfile,
    ) -> CachedRecipe:
        _validate_binding(origin, lockfile)
        return self._load_generation(_generation_key(origin, lockfile))

    def load_locator(self, locator: str, target: str) -> CachedRecipe:
        pointer = self.root / "locators" / _locator_key(locator, target)
        try:
            raw = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(
                f"frozen recipe is absent from cache: {locator}"
            ) from exc
        table = require_table(raw, "recipeCache.locator")
        require_keys(table, {"locator", "target", "generation"}, "recipeCache.locator")
        if set(table) != {"locator", "target", "generation"}:
            raise SecurityError("cached recipe locator has unknown fields")
        if table["locator"] != locator or table["target"] != target:
            raise SecurityError("cached recipe locator does not match its request")
        generation = require_string(
            table["generation"], "recipeCache.locator.generation"
        )
        if len(generation) != 64 or any(
            character not in "0123456789abcdef" for character in generation
        ):
            raise SecurityError("cached recipe locator generation is invalid")
        return self._load_generation(generation)

    def _point(self, locator: str, target: str, generation: str) -> None:
        atomic_write(
            self.root / "locators" / _locator_key(locator, target),
            canonical_json_bytes(
                {"locator": locator, "target": target, "generation": generation}
            ),
        )

    def _load_generation(self, generation: str) -> CachedRecipe:
        directory = self.root / "snapshots" / generation
        if directory.is_symlink() or not directory.is_dir():
            raise ValidationError("frozen recipe generation is absent from cache")
        try:
            raw = json.loads((directory / METADATA_FILE).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SecurityError("cached recipe metadata is invalid") from exc
        table = require_table(raw, "recipeCache")
        require_keys(
            table,
            {"cacheVersion", "generation", "lockDigest", "files"},
            "recipeCache",
        )
        if set(table) != {"cacheVersion", "generation", "lockDigest", "files"}:
            raise SecurityError("cached recipe metadata has unknown fields")
        if (
            require_int(table["cacheVersion"], "recipeCache.cacheVersion")
            != RECIPE_CACHE_VERSION
        ):
            raise SecurityError("cached recipe version is unsupported")
        if table["generation"] != generation:
            raise SecurityError("cached recipe generation does not match its path")
        expected_lock_digest = validate_digest(
            table["lockDigest"], "recipeCache.lockDigest"
        )
        lockfile = load_lockfile(directory / LOCKFILE_NAME)
        if lockfile.digest != expected_lock_digest:
            raise SecurityError("cached recipe lock digest mismatch")
        if lockfile.recipe is None:
            raise SecurityError("cached recipe lock has no origin")
        entries = _parse_entries(table["files"])
        recipe_root = directory / "recipe"
        actual_entries = full_recipe_context_entries(recipe_root)
        if actual_entries != entries:
            raise SecurityError("cached recipe files do not match metadata")
        origin = _origin(lockfile.recipe)
        manifest = load_manifest(recipe_root / MANIFEST_NAME)
        snapshot = create_recipe_snapshot(
            recipe_root,
            manifest,
            kind=origin.kind,
            source=origin.source,
            revision=origin.revision,
            ref=origin.ref,
            tracking=origin.tracking,
            entry=origin.entry,
            path=origin.path,
        )
        _validate_binding(snapshot.origin, lockfile)
        return CachedRecipe(snapshot=snapshot, lockfile=lockfile)


def database_locator(revision: str, entry: str) -> str:
    return f"database:{revision}:{entry}"


def github_locator(source: str, requested_ref: str | None) -> str:
    return f"github:{source}:{requested_ref or '<default>'}"


def _origin_locator(origin: RecipeOrigin) -> str:
    return "origin:" + json.dumps(
        _origin_dict(origin),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _generation_key(origin: RecipeOrigin, lockfile: Lockfile) -> str:
    payload = canonical_json_bytes(
        {
            "origin": _origin_dict(origin),
            "target": lockfile.target,
            "lockDigest": lockfile.digest,
        }
    )
    return sha256_digest(payload).removeprefix("sha256:")


def _locator_key(locator: str, target: str) -> str:
    return (
        sha256_digest(f"{locator}\0{target}".encode()).removeprefix("sha256:") + ".json"
    )


def _origin_dict(origin: RecipeOrigin) -> dict[str, Any]:
    return {
        "kind": origin.kind,
        "source": origin.source,
        "revision": origin.revision,
        "entry": origin.entry,
        "path": origin.path,
        "ref": origin.ref,
        "tracking": origin.tracking,
        "version": origin.version,
        "manifestDigest": origin.manifest_digest,
        "templateDigest": origin.template_digest,
    }


def _origin(recipe: RecipeLock) -> RecipeOrigin:
    return RecipeOrigin(
        kind=recipe.kind,
        source=recipe.source,
        revision=recipe.revision,
        entry=recipe.entry,
        path=recipe.path,
        ref=recipe.ref,
        tracking=recipe.tracking,
        version=recipe.version,
        manifest_digest=recipe.manifest_digest,
        template_digest=recipe.template_digest,
    )


def _validate_binding(origin: RecipeOrigin, lockfile: Lockfile) -> None:
    recipe = lockfile.recipe
    if recipe is None or _origin(recipe) != origin:
        raise ValidationError("cached recipe snapshot does not match its lock origin")
    if lockfile.manifest_digest != origin.manifest_digest:
        raise ValidationError("cached recipe lock does not match its manifest")


def _entry_dict(entry: RecipeSnapshotEntry) -> dict[str, Any]:
    return {
        "path": entry.path,
        "type": entry.type,
        "mode": entry.mode,
        "size": entry.size,
        "digest": entry.digest,
    }


def _parse_entries(value: Any) -> tuple[RecipeSnapshotEntry, ...]:
    entries = []
    for index, raw in enumerate(require_array(value, "recipeCache.files")):
        path = f"recipeCache.files[{index}]"
        table = require_table(raw, path)
        require_keys(table, {"path", "type", "mode", "size", "digest"}, path)
        if set(table) != {"path", "type", "mode", "size", "digest"}:
            raise SecurityError("cached recipe file metadata has unknown fields")
        relative = safe_relative_path(table["path"], f"{path}.path")
        entry_type = require_string(table["type"], f"{path}.type")
        if entry_type not in {"file", "directory"}:
            raise SecurityError("cached recipe file type is invalid")
        digest = table["digest"]
        if entry_type == "file":
            digest = validate_digest(digest, f"{path}.digest")
        elif digest is not None:
            raise SecurityError("cached recipe directory has a digest")
        entries.append(
            RecipeSnapshotEntry(
                path=relative,
                type=entry_type,  # type: ignore[arg-type]
                mode=require_int(table["mode"], f"{path}.mode", minimum=0),
                size=require_int(table["size"], f"{path}.size", minimum=0),
                digest=digest,
            )
        )
    if [entry.path for entry in entries] != sorted(entry.path for entry in entries):
        raise SecurityError("cached recipe file metadata is not sorted")
    if len({entry.path for entry in entries}) != len(entries):
        raise SecurityError("cached recipe file metadata has duplicates")
    return tuple(entries)
