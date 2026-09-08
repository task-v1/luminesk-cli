from __future__ import annotations

from pathlib import Path

import pytest

from luminesk_cli.domain.errors import SecurityError
from luminesk_cli.infrastructure.cache import ContentCache, digest_file


def test_cache_stores_and_verifies_content(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"verified content")
    digest, size = digest_file(source)
    cache = ContentCache(tmp_path / "cache")

    cached = cache.store(source, digest)

    assert cached.size == size
    assert cache.restore(digest) == cached
    assert cache.verify() == (1, ())


def test_cache_rejects_and_removes_corruption(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"original")
    digest, _ = digest_file(source)
    cache = ContentCache(tmp_path / "cache")
    cached = cache.store(source, digest)
    cached.path.write_bytes(b"corrupt")

    with pytest.raises(SecurityError, match="cached blob digest mismatch"):
        cache.restore(digest)

    assert not cached.path.exists()
