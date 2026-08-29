"""Content-addressed blob cache with verification on every restore."""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from filelock import FileLock

from luminesk_cli.domain.errors import SecurityError
from luminesk_cli.domain.primitives import validate_digest

HASH_CHUNK_SIZE = 256 * 1024


@dataclass(slots=True, frozen=True)
class CachedBlob:
    path: Path
    digest: str
    size: int


def digest_file(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0

    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK_SIZE):
            hasher.update(chunk)
            size += len(chunk)

    return f"sha256:{hasher.hexdigest()}", size


class ContentCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.blobs = root / "blobs" / "sha256"
        self.locks = root / "locks"

    def path_for(self, digest: str) -> Path:
        validate_digest(digest, "digest")
        hexadecimal = digest.removeprefix("sha256:")
        return self.blobs / hexadecimal[:2] / hexadecimal

    def lock_for(self, digest: str) -> FileLock:
        validate_digest(digest, "digest")
        self.locks.mkdir(parents=True, exist_ok=True)
        hexadecimal = digest.removeprefix("sha256:")
        return FileLock(self.locks / f"{hexadecimal}.lock")

    def restore(self, digest: str) -> CachedBlob | None:
        path = self.path_for(digest)

        if not path.is_file():
            return None

        actual, size = digest_file(path)

        if actual != digest:
            path.unlink(missing_ok=True)
            raise SecurityError(
                "cached blob digest mismatch",
                expected=digest,
                actual=actual,
                path=str(path),
            )

        return CachedBlob(path=path, digest=digest, size=size)

    def store(self, source: Path, digest: str) -> CachedBlob:
        actual, size = digest_file(source)

        if actual != digest:
            raise SecurityError(
                "blob digest mismatch before cache commit",
                expected=digest,
                actual=actual,
                path=str(source),
            )

        destination = self.path_for(digest)

        with self.lock_for(digest):
            cached = self.restore(digest)

            if cached is not None:
                return cached

            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(f".tmp-{os.getpid()}")

            try:
                shutil.copyfile(source, temporary)
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)

        return CachedBlob(path=destination, digest=digest, size=size)

    def verify(self) -> tuple[int, tuple[str, ...]]:
        count = 0
        corrupt = []

        if not self.blobs.exists():
            return 0, ()

        for path in self.blobs.glob("*/*"):
            if not path.is_file():
                continue

            count += 1
            expected = f"sha256:{path.name}"
            actual, _ = digest_file(path)

            if actual != expected:
                corrupt.append(str(path))

        return count, tuple(corrupt)
