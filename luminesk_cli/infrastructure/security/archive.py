"""Archive extraction that rejects links, special files, escapes, and bombs."""

from __future__ import annotations

import shutil
import stat
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from luminesk_cli.domain.errors import SecurityError
from luminesk_cli.domain.primitives import safe_relative_path


@dataclass(slots=True, frozen=True)
class ArchiveLimits:
    max_files: int = 10_000
    max_file_size: int = 512 * 1024 * 1024
    max_total_size: int = 2 * 1024 * 1024 * 1024
    max_compression_ratio: int = 200


def extract_archive(
    archive: Path,
    destination: Path,
    *,
    limits: ArchiveLimits = ArchiveLimits(),
) -> tuple[Path, ...]:
    destination.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(archive):
        return _extract_zip(archive, destination, limits)

    if tarfile.is_tarfile(archive):
        return _extract_tar(archive, destination, limits)

    raise SecurityError("source marked extract is not a supported ZIP/TAR archive")


def _checked_destination(root: Path, name: str) -> Path:
    normalized = safe_relative_path(name.rstrip("/"), "archive.member.path")
    target = (root / normalized).resolve()

    if not target.is_relative_to(root.resolve()):
        raise SecurityError("archive member escapes extraction root", path=name)

    return target


def _check_limits(
    count: int,
    size: int,
    total: int,
    compressed_size: int,
    limits: ArchiveLimits,
) -> None:
    if count > limits.max_files:
        raise SecurityError("archive contains too many files", count=count)

    if size > limits.max_file_size:
        raise SecurityError("archive member exceeds size limit", size=size)

    if total > limits.max_total_size:
        raise SecurityError("archive expanded size exceeds limit", size=total)

    if compressed_size > 0 and size > compressed_size * limits.max_compression_ratio:
        raise SecurityError("archive member exceeds compression-ratio limit")


def _extract_zip(
    archive: Path,
    destination: Path,
    limits: ArchiveLimits,
) -> tuple[Path, ...]:
    extracted = []
    total = 0

    with zipfile.ZipFile(archive) as handle:
        members = handle.infolist()

        for count, member in enumerate(members, start=1):
            mode = member.external_attr >> 16

            if stat.S_ISLNK(mode):
                raise SecurityError("archive symlinks are forbidden", path=member.filename)

            total += member.file_size
            _check_limits(
                count,
                member.file_size,
                total,
                member.compress_size,
                limits,
            )
            target = _checked_destination(destination, member.filename)

            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            with handle.open(member, "r") as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=256 * 1024)

            extracted.append(target)

    return tuple(extracted)


def _extract_tar(
    archive: Path,
    destination: Path,
    limits: ArchiveLimits,
) -> tuple[Path, ...]:
    extracted = []
    total = 0

    with tarfile.open(archive, "r:*") as handle:
        for count, member in enumerate(handle, start=1):
            if member.issym() or member.islnk():
                raise SecurityError("archive links are forbidden", path=member.name)

            if not (member.isfile() or member.isdir()):
                raise SecurityError(
                    "archive special files are forbidden", path=member.name
                )

            total += member.size
            _check_limits(count, member.size, total, archive.stat().st_size, limits)
            target = _checked_destination(destination, member.name)

            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            source = handle.extractfile(member)

            if source is None:
                raise SecurityError("cannot read archive member", path=member.name)

            target.parent.mkdir(parents=True, exist_ok=True)

            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=256 * 1024)

            extracted.append(target)

    return tuple(extracted)
