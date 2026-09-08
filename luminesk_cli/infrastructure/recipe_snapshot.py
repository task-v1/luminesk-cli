"""Selective, bounded canonical recipe snapshot creation and persistence."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.manifest import (
    MANIFEST_NAME,
    LocalFileOptions,
    Manifest,
    load_manifest,
)
from luminesk_cli.domain.primitives import safe_relative_path
from luminesk_cli.domain.recipe import (
    RecipeOrigin,
    RecipeSnapshot,
    RecipeSnapshotEntry,
)
from luminesk_cli.infrastructure.cache import digest_file
from luminesk_cli.infrastructure.template import read_template_tree

MAX_SNAPSHOT_FILES = 20_000
MAX_SNAPSHOT_SIZE = 256 * 1024 * 1024


def declared_recipe_assets(manifest: Manifest) -> tuple[str, ...]:
    """Return every path whose bytes are part of the declarative recipe."""

    paths: list[str] = []
    if manifest.template is not None:
        paths.append(manifest.template)
    paths.extend(file_spec.source for file_spec in manifest.files)
    paths.extend(
        source.options.path
        for source in manifest.sources
        if isinstance(source.options, LocalFileOptions)
    )
    if manifest.build is not None:
        paths.append(manifest.build.file)
    return tuple(dict.fromkeys(paths))


def full_recipe_context_entries(root: Path) -> tuple[RecipeSnapshotEntry, ...]:
    """Describe a bounded build context for verified offline reuse."""

    recipe_root = root.resolve()
    collector = _SnapshotCollector(recipe_root)
    for child in sorted(recipe_root.iterdir(), key=lambda item: item.name):
        if child.name in {".git", ".luminesk_cli"}:
            continue
        collector.add(child.name)
    return collector.entries()


def load_verified_installed_recipe(root: Path, lockfile: Lockfile) -> RecipeSnapshot:
    """Load the canonical recipe only after checking its root mirror and lock."""

    from luminesk_cli.infrastructure.state import RECIPE_DIRECTORY, state_directory

    recipe = lockfile.recipe
    if recipe is None:
        raise ValidationError("instance lock has no complete recipe origin")
    canonical = state_directory(root) / RECIPE_DIRECTORY
    manifest = load_manifest(canonical / MANIFEST_NAME)
    snapshot = create_recipe_snapshot(
        canonical,
        manifest,
        kind=recipe.kind,
        source=recipe.source,
        revision=recipe.revision,
        ref=recipe.ref,
        tracking=recipe.tracking,
        entry=recipe.entry,
        path=recipe.path,
    )
    if (
        snapshot.origin.version != recipe.version
        or snapshot.origin.manifest_digest != recipe.manifest_digest
        or snapshot.origin.template_digest != recipe.template_digest
        or lockfile.manifest_digest != recipe.manifest_digest
    ):
        raise ValidationError(
            "Canonical installed recipe differs from the locked recipe snapshot. "
            "Run `nesk diff` before continuing."
        )
    root_manifest = root / MANIFEST_NAME
    if not root_manifest.is_file() or root_manifest.is_symlink():
        raise ValidationError(
            "Installed luminesk.toml is missing or unsafe. Run `nesk diff`."
        )
    root_digest, _ = digest_file(root_manifest)
    if root_digest != recipe.manifest_digest:
        raise ValidationError(
            "Installed luminesk.toml differs from the locked recipe snapshot. "
            "Run `nesk diff` before continuing."
        )
    return snapshot


def create_recipe_snapshot(
    root: Path,
    manifest: Manifest,
    *,
    kind: str = "local",
    source: str = "local",
    revision: str | None = None,
    tracking: bool = False,
    ref: str | None = None,
    entry: str | None = None,
    path: str | None = None,
) -> RecipeSnapshot:
    recipe_root = root.resolve()
    manifest_path = recipe_root / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValidationError("recipe root has no regular luminesk.toml")
    digest, _ = digest_file(manifest_path)
    if digest != manifest.digest:
        raise ValidationError("recipe manifest changed after validation")
    if kind not in {"database", "github", "local"}:
        raise ValidationError(f"unsupported recipe origin kind: {kind}")

    template_tree = read_template_tree(recipe_root, manifest)
    template_digest = template_tree.digest if template_tree is not None else None
    origin = RecipeOrigin(
        kind=kind,  # type: ignore[arg-type]
        source=source,
        revision=revision or manifest.digest,
        ref=ref,
        tracking=tracking,
        entry=entry,
        path=path,
        version=manifest.package.version,
        manifest_digest=manifest.digest,
        template_digest=template_digest,
    )
    collector = _SnapshotCollector(recipe_root)
    collector.add(MANIFEST_NAME)

    optional_data = {
        file_spec.source for file_spec in manifest.files if file_spec.mode == "data"
    }
    for relative in declared_recipe_assets(manifest):
        if relative in optional_data and not (recipe_root / relative).exists():
            continue
        collector.add(relative)

    return RecipeSnapshot(
        root=recipe_root,
        manifest=manifest,
        origin=origin,
        entries=collector.entries(),
    )


def stage_recipe_snapshot(snapshot: RecipeSnapshot, destination: Path) -> None:
    if destination.exists():
        raise ValidationError("recipe snapshot staging target already exists")
    destination.mkdir(parents=True)

    for entry in snapshot.entries:
        source = snapshot.root / entry.path
        if not source.resolve().is_relative_to(snapshot.root):
            raise SecurityError(
                "recipe snapshot source escapes recipe root", path=entry.path
            )
        target = destination / entry.path
        status = source.lstat()
        if stat.S_ISLNK(status.st_mode):
            raise SecurityError(
                "recipe snapshot source became a symlink", path=entry.path
            )

        if entry.type == "directory":
            if not stat.S_ISDIR(status.st_mode):
                raise SecurityError(
                    "recipe snapshot directory changed type", path=entry.path
                )
            target.mkdir(parents=True, exist_ok=True)
            target.chmod(entry.mode)
            continue

        if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
            raise SecurityError("recipe snapshot file changed type", path=entry.path)
        digest, size = digest_file(source)
        if digest != entry.digest or size != entry.size:
            raise ValidationError(
                "recipe snapshot source changed after validation", path=entry.path
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(entry.mode)


class _SnapshotCollector:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._entries: dict[str, RecipeSnapshotEntry] = {}
        self._files = 0
        self._size = 0

    def add(self, relative: str) -> None:
        safe = safe_relative_path(relative, "recipe.snapshot.path")
        source = self.root / safe
        if not source.resolve().is_relative_to(self.root):
            raise SecurityError("recipe snapshot asset escapes recipe root", path=safe)
        try:
            status = source.lstat()
        except OSError as exc:
            raise ValidationError(
                "declared recipe snapshot asset does not exist", path=safe
            ) from exc
        if stat.S_ISLNK(status.st_mode):
            raise SecurityError("recipe snapshot symlinks are forbidden", path=safe)
        if stat.S_ISDIR(status.st_mode):
            self._add_directory(safe, source, status)
            for child in sorted(
                source.rglob("*"),
                key=lambda item: item.relative_to(self.root).as_posix(),
            ):
                child_relative = child.relative_to(self.root).as_posix()
                child_status = child.lstat()
                if stat.S_ISLNK(child_status.st_mode):
                    raise SecurityError(
                        "recipe snapshot symlinks are forbidden",
                        path=child_relative,
                    )
                if stat.S_ISDIR(child_status.st_mode):
                    self._add_directory(child_relative, child, child_status)
                elif stat.S_ISREG(child_status.st_mode):
                    self._add_file(child_relative, child, child_status)
                else:
                    raise SecurityError(
                        "recipe snapshot contains a special file",
                        path=child_relative,
                    )
        elif stat.S_ISREG(status.st_mode):
            self._add_file(safe, source, status)
        else:
            raise SecurityError("recipe snapshot asset is a special file", path=safe)

    def _add_directory(
        self, relative: str, source: Path, status: os.stat_result
    ) -> None:
        del source
        mode = stat.S_IMODE(status.st_mode)
        self._entries.setdefault(
            relative,
            RecipeSnapshotEntry(relative, "directory", mode, 0, None),
        )

    def _add_file(self, relative: str, source: Path, status: os.stat_result) -> None:
        if relative in self._entries:
            return
        if status.st_nlink != 1:
            raise SecurityError(
                "recipe snapshot hardlinks are forbidden", path=relative
            )
        self._files += 1
        if self._files > MAX_SNAPSHOT_FILES:
            raise SecurityError("recipe snapshot contains too many files")
        size = status.st_size
        self._size += size
        if self._size > MAX_SNAPSHOT_SIZE:
            raise SecurityError("recipe snapshot exceeds total size limit")
        digest, measured_size = digest_file(source)
        if measured_size != size:
            raise ValidationError(
                "recipe snapshot file changed while reading", path=relative
            )
        self._entries[relative] = RecipeSnapshotEntry(
            relative,
            "file",
            stat.S_IMODE(status.st_mode),
            size,
            digest,
        )

    def entries(self) -> tuple[RecipeSnapshotEntry, ...]:
        return tuple(self._entries[path] for path in sorted(self._entries))
