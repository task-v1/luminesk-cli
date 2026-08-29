"""Declarative package assembly and optional isolated Dockerfile builds."""

from __future__ import annotations

import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from luminesk_cli.domain.errors import SecurityError, TransactionError, ValidationError
from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.manifest import Build, Check, FileSpec, Manifest
from luminesk_cli.domain.package import PackageFile, PackageMetadata, ServerPackage
from luminesk_cli.infrastructure.cache import ContentCache, digest_file
from luminesk_cli.infrastructure.package import write_package
from luminesk_cli.infrastructure.security.archive import ArchiveLimits, extract_archive

MAX_BUILD_CONTEXT_FILES = 20_000
MAX_BUILD_CONTEXT_SIZE = 1024 * 1024 * 1024


class DockerfileBuilder:
    """Run a declared Dockerfile without host mounts, socket, or privileges."""

    def build(self, recipe_root: Path, spec: Build, destination: Path) -> None:
        with tempfile.TemporaryDirectory(prefix="nesk-build-context-") as context_name:
            context = Path(context_name)
            _copy_build_context(recipe_root, context)
            dockerfile = context / spec.file

            if not dockerfile.is_file() or dockerfile.is_symlink():
                raise ValidationError(
                    "declared Dockerfile is not a regular context file",
                    path=spec.file,
                )

            destination.mkdir(parents=True, exist_ok=True)
            network = "default" if spec.permissions.network else "none"
            argv = [
                "docker",
                "build",
                "--file",
                str(dockerfile),
                "--network",
                network,
                "--output",
                f"type=local,dest={destination}",
                str(context),
            ]

            try:
                result = subprocess.run(
                    argv,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=spec.timeout,
                    shell=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise TransactionError(f"Dockerfile build failed: {exc}") from exc

            if result.returncode != 0:
                raise TransactionError(
                    "Dockerfile build failed",
                    exit_code=result.returncode,
                    stderr=result.stderr[-4000:],
                )


class DeclarativeBuilder:
    def __init__(
        self,
        cache: ContentCache,
        *,
        dockerfile_builder: DockerfileBuilder | None = None,
        archive_limits: ArchiveLimits = ArchiveLimits(),
    ) -> None:
        self.cache = cache
        self.dockerfile_builder = dockerfile_builder or DockerfileBuilder()
        self.archive_limits = archive_limits

    def build(
        self,
        manifest: Manifest,
        lockfile: Lockfile,
        recipe_root: Path,
        output: Path,
        *,
        inputs: Mapping[str, str | int | bool] | None = None,
    ) -> ServerPackage:
        if manifest.digest != lockfile.manifest_digest:
            raise ValidationError("lockfile does not match manifest")

        values = _resolve_inputs(manifest, inputs or {})

        with tempfile.TemporaryDirectory(prefix="nesk-package-stage-") as stage_name:
            payload = Path(stage_name) / "payload"
            payload.mkdir()
            ownership: dict[str, str] = {}

            if manifest.build is not None:
                self.dockerfile_builder.build(recipe_root, manifest.build, payload)
                _record_tree(payload, payload, ownership, "managed")

            for source in manifest.sources:
                resolved = lockfile.sources.get(source.id)

                if resolved is None:
                    if source.platforms and lockfile.target not in source.platforms:
                        continue

                    raise ValidationError(f"lockfile is missing source {source.id}")

                blob = self.cache.restore(resolved.digest)

                if blob is None:
                    raise ValidationError(
                        f"source {source.id} is absent from content cache"
                    )

                target = payload / source.target

                if source.extract:
                    if target.exists() and not target.is_dir():
                        raise ValidationError(
                            f"source target conflicts with existing file: {source.target}"
                        )

                    before = set(ownership)
                    target.mkdir(parents=True, exist_ok=True)
                    extract_archive(
                        blob.path,
                        target,
                        limits=self.archive_limits,
                    )
                    _record_tree(payload, target, ownership, "managed", previous=before)
                else:
                    _ensure_new_target(target, source.target)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(blob.path, target)
                    ownership[source.target] = "managed"

            for file_spec in manifest.files:
                _apply_recipe_file(
                    recipe_root,
                    payload,
                    file_spec,
                    values,
                    ownership,
                )

            _run_file_checks(payload, manifest.checks, phase="post-build")
            package_files = _package_files(payload, ownership)
            metadata = PackageMetadata(
                name=manifest.package.name,
                version=manifest.package.version,
                manifest_digest=manifest.digest,
                lock_digest=lockfile.digest,
                target=lockfile.target,
                recipe_revision=(
                    lockfile.recipe.revision if lockfile.recipe is not None else None
                ),
                files=package_files,
            )
            return write_package(output, payload, metadata)


def _resolve_inputs(
    manifest: Manifest,
    overrides: Mapping[str, str | int | bool],
) -> dict[str, str | int | bool]:
    declared = {item.name: item for item in manifest.inputs}
    unknown = sorted(set(overrides) - set(declared))

    if unknown:
        raise ValidationError(f"unknown input: {unknown[0]}")

    values: dict[str, str | int | bool] = {}

    for name, spec in declared.items():
        value = overrides.get(name, spec.default)

        if value is None:
            if spec.required:
                raise ValidationError(f"required input has no value: {name}")

            continue

        expected_type = {"string": str, "integer": int, "boolean": bool}[spec.type]

        if not isinstance(value, expected_type) or (
            spec.type == "integer" and isinstance(value, bool)
        ):
            raise ValidationError(f"input {name} has the wrong type")

        if isinstance(value, int) and not isinstance(value, bool):
            if spec.minimum is not None and value < spec.minimum:
                raise ValidationError(f"input {name} is below its minimum")

            if spec.maximum is not None and value > spec.maximum:
                raise ValidationError(f"input {name} is above its maximum")

        if isinstance(value, str) and spec.pattern is not None:
            if re.fullmatch(spec.pattern, value) is None:
                raise ValidationError(f"input {name} does not match its pattern")

        values[name] = value

    return values


def _render_template(content: bytes, values: Mapping[str, str | int | bool]) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("template files must be UTF-8") from exc

    pattern = re.compile(r"\$\{input\.([A-Za-z0-9_-]+)\}")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)

        if name not in values:
            raise ValidationError(f"template references missing input: {name}")

        value = values[name]
        return str(value).lower() if isinstance(value, bool) else str(value)

    return pattern.sub(replace, text).encode("utf-8")


def _apply_recipe_file(
    recipe_root: Path,
    payload: Path,
    spec: FileSpec,
    values: Mapping[str, str | int | bool],
    ownership: dict[str, str],
) -> None:
    target = payload / spec.target

    if spec.mode == "data" and not (recipe_root / spec.source).exists():
        _ensure_new_target(target, spec.target)
        target.mkdir(parents=True)
        ownership[spec.target] = spec.mode
        return

    source = (recipe_root / spec.source).resolve()

    if not source.is_relative_to(recipe_root.resolve()) or source.is_symlink():
        raise SecurityError("recipe file escapes recipe root", path=spec.source)

    if not source.exists():
        raise ValidationError("recipe file does not exist", path=spec.source)

    _ensure_new_target(target, spec.target)

    if source.is_dir():
        target.mkdir(parents=True)
        ownership[spec.target] = spec.mode

        for item in source.rglob("*"):
            if item.is_symlink():
                raise SecurityError("recipe symlinks are forbidden", path=str(item))

            relative = item.relative_to(source)
            destination = target / relative

            if item.is_dir():
                destination.mkdir()
                ownership[destination.relative_to(payload).as_posix()] = spec.mode
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            content = item.read_bytes()

            if spec.template:
                content = _render_template(content, values)

            destination.write_bytes(content)
            ownership[destination.relative_to(payload).as_posix()] = spec.mode
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_bytes()

        if spec.template:
            content = _render_template(content, values)

        target.write_bytes(content)
        ownership[spec.target] = spec.mode
    else:
        raise SecurityError("recipe source is not a regular file or directory")

    if spec.executable:
        target.chmod(target.stat().st_mode | stat.S_IXUSR)


def _ensure_new_target(target: Path, relative: str) -> None:
    if target.exists() or target.is_symlink():
        raise ValidationError(f"package target is declared more than once: {relative}")


def _record_tree(
    payload: Path,
    root: Path,
    ownership: dict[str, str],
    mode: str,
    *,
    previous: set[str] | None = None,
) -> None:
    previous = previous or set()

    for path in root.rglob("*"):
        if path.is_symlink():
            raise SecurityError("build output symlinks are forbidden", path=str(path))

        if not (path.is_file() or path.is_dir()):
            raise SecurityError("build output special files are forbidden", path=str(path))

        relative = path.relative_to(payload).as_posix()

        if relative in previous:
            raise ValidationError(f"build output collision: {relative}")

        ownership[relative] = mode


def _package_files(
    payload: Path,
    ownership: Mapping[str, str],
) -> tuple[PackageFile, ...]:
    result = []

    for path in sorted(payload.rglob("*")):
        relative = path.relative_to(payload).as_posix()
        mode = stat.S_IMODE(path.stat().st_mode)
        owner = ownership.get(relative, "managed")

        if owner not in {"managed", "preserve", "generated", "data"}:
            raise ValidationError(f"invalid ownership mode for {relative}")

        if path.is_dir():
            result.append(
                PackageFile(
                    path=relative,
                    type="directory",
                    mode=mode,
                    size=0,
                    digest=None,
                    ownership=owner,  # type: ignore[arg-type]
                )
            )
            continue

        digest, size = digest_file(path)
        result.append(
            PackageFile(
                path=relative,
                type="file",
                mode=mode,
                size=size,
                digest=digest,
                ownership=owner,  # type: ignore[arg-type]
            )
        )

    return tuple(result)


def _run_file_checks(payload: Path, checks: Sequence[Check], *, phase: str) -> None:
    for check in checks:
        if check.phase != phase or check.kind != "file" or check.path is None:
            continue

        exists = (payload / check.path).is_file()

        if check.required and not exists:
            raise ValidationError(
                f"required {phase} file check failed: {check.id}", path=check.path
            )


def _copy_build_context(source: Path, destination: Path) -> None:
    count = 0
    size = 0
    excluded_names = {".git", ".luminesk_cli", "worlds", "logs"}

    for path in source.rglob("*"):
        relative = path.relative_to(source)

        if any(part in excluded_names for part in relative.parts):
            continue

        if path.is_symlink():
            raise SecurityError("build context symlinks are forbidden", path=str(relative))

        target = destination / relative
        count += 1

        if count > MAX_BUILD_CONTEXT_FILES:
            raise SecurityError("build context contains too many files")

        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        if not path.is_file():
            raise SecurityError("build context contains a special file", path=str(relative))

        size += path.stat().st_size

        if size > MAX_BUILD_CONTEXT_SIZE:
            raise SecurityError("build context exceeds size limit")

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
