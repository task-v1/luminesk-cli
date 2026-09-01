"""Bounded, deterministic recipe template trees."""

from __future__ import annotations

import json
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.domain.manifest import Manifest
from luminesk_cli.domain.primitives import sha256_digest
from luminesk_cli.infrastructure.cache import digest_file

MAX_TEMPLATE_FILES = 4_096
MAX_TEMPLATE_FILE_SIZE = 16 * 1024 * 1024
MAX_TEMPLATE_SIZE = 64 * 1024 * 1024
INPUT_PATTERN = re.compile(r"\$\{input\.([A-Za-z0-9_-]+)}")
INPUT_BYTES_PATTERN = re.compile(rb"\$\{input\.([A-Za-z0-9_-]+)}")


@dataclass(slots=True, frozen=True)
class TemplateEntry:
    source_path: Path
    source_relative: str
    target: str
    type: str
    size: int
    digest: str | None
    render: bool = False


@dataclass(slots=True, frozen=True)
class TemplateTree:
    root: Path
    entries: tuple[TemplateEntry, ...]
    digest: str


def read_template_tree(recipe_root: Path, manifest: Manifest) -> TemplateTree | None:
    if manifest.template is None:
        return None

    recipe = recipe_root.resolve()
    root = recipe / manifest.template
    try:
        root_status = root.lstat()
    except OSError as exc:
        raise ValidationError(
            "declared template directory does not exist",
            path=manifest.template,
        ) from exc
    if stat.S_ISLNK(root_status.st_mode):
        raise SecurityError("template directory may not be a symlink")
    if not stat.S_ISDIR(root_status.st_mode):
        raise ValidationError("declared template path is not a directory")
    if not root.resolve().is_relative_to(recipe):
        raise SecurityError("template directory escapes recipe root")

    entries: list[TemplateEntry] = []
    targets: set[str] = set()
    file_count = 0
    total_size = 0

    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        try:
            status = path.lstat()
        except OSError as exc:
            raise SecurityError("cannot inspect template entry", path=relative) from exc
        if stat.S_ISLNK(status.st_mode):
            raise SecurityError("template symlinks are forbidden", path=relative)

        if stat.S_ISDIR(status.st_mode):
            target = relative
            entry_type = "directory"
            size = 0
            digest = None
            render = False
        elif stat.S_ISREG(status.st_mode):
            if status.st_nlink != 1:
                raise SecurityError("template hardlinks are forbidden", path=relative)
            file_count += 1
            if file_count > MAX_TEMPLATE_FILES:
                raise SecurityError("template contains too many files")
            size = status.st_size
            if size > MAX_TEMPLATE_FILE_SIZE:
                raise SecurityError(
                    "template file exceeds size limit",
                    path=relative,
                    size=size,
                )
            total_size += size
            if total_size > MAX_TEMPLATE_SIZE:
                raise SecurityError("template tree exceeds total size limit")
            render = relative.endswith(".tmpl")
            target = relative.removesuffix(".tmpl") if render else relative
            if not target or target.endswith("/"):
                raise ValidationError(
                    "template suffix produces an empty target", path=relative
                )
            entry_type = "file"
            digest, _ = digest_file(path)
        else:
            raise SecurityError("template contains a special file", path=relative)

        if target in targets:
            raise ValidationError(
                "template entries produce the same target",
                path=target,
            )
        targets.add(target)
        entries.append(
            TemplateEntry(
                source_path=path,
                source_relative=relative,
                target=target,
                type=entry_type,
                size=size,
                digest=digest,
                render=render,
            )
        )

    canonical = [
        {
            "digest": entry.digest,
            "path": entry.source_relative,
            "target": entry.target,
            "type": entry.type,
        }
        for entry in entries
    ]
    digest = sha256_digest(
        (json.dumps(canonical, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    return TemplateTree(root=root, entries=tuple(entries), digest=digest)


def materialize_template(
    tree: TemplateTree,
    payload: Path,
    manifest: Manifest,
    inputs: Mapping[str, str | int | bool],
    ownership: dict[str, str],
) -> None:
    for entry in tree.entries:
        target = payload / entry.target
        _reject_collision(payload, target, entry.target)
        mode = _ownership_mode(manifest, entry.target, "generated")

        if entry.type == "directory":
            target.mkdir(parents=True)
            ownership[entry.target] = mode
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        content = entry.source_path.read_bytes()
        contains_secret = entry.render and references_secret_input(content, manifest)
        if entry.render:
            content = render_template(content, inputs, path=entry.source_relative)
        target.touch(mode=0o600 if contains_secret else 0o666)
        target.write_bytes(content)
        if _path_matches(entry.target, manifest.ownership.executable):
            target.chmod(target.stat().st_mode | stat.S_IXUSR)
        ownership[entry.target] = mode


def references_secret_input(content: bytes, manifest: Manifest) -> bool:
    secret_names = {spec.name for spec in manifest.inputs if spec.secret}
    return any(
        match.group(1).decode("ascii") in secret_names
        for match in INPUT_BYTES_PATTERN.finditer(content)
    )


def apply_ownership_overrides(
    payload: Path,
    manifest: Manifest,
    ownership: dict[str, str],
) -> None:
    for relative in tuple(ownership):
        ownership[relative] = _ownership_mode(
            manifest,
            relative,
            ownership[relative],
        )
        if _path_matches(relative, manifest.ownership.executable):
            path = payload / relative
            if path.is_file() and not path.is_symlink():
                path.chmod(path.stat().st_mode | stat.S_IXUSR)


def render_template(
    content: bytes,
    inputs: Mapping[str, str | int | bool],
    *,
    path: str,
) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(".tmpl files must be UTF-8", path=path) from exc

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in inputs:
            raise ValidationError(
                f"template references missing input: {name}", path=path
            )
        value = inputs[name]
        return str(value).lower() if isinstance(value, bool) else str(value)

    return INPUT_PATTERN.sub(replace, text).encode("utf-8")


def _ownership_mode(manifest: Manifest, path: str, default: str) -> str:
    if _path_matches(path, manifest.ownership.data):
        return "data"
    if _path_matches(path, manifest.ownership.preserve):
        return "preserve"
    return default


def _path_matches(path: str, policies: tuple[str, ...]) -> bool:
    return any(path == policy or path.startswith(f"{policy}/") for policy in policies)


def _reject_collision(payload: Path, target: Path, relative: str) -> None:
    if target.exists() or target.is_symlink():
        raise ValidationError(
            f"template target collides with package content: {relative}"
        )

    for current in target.parents:
        if current == payload:
            break
        if current.exists() and not current.is_dir():
            raise ValidationError(
                f"template target parent collides with package content: {relative}"
            )
