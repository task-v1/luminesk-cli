from __future__ import annotations

from pathlib import Path

import pytest

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.lockfile import (
    LOCKFILE_NAME,
    Lockfile,
    ResolvedSource,
    RuntimeLock,
    load_lockfile,
    parse_lockfile,
    write_lockfile,
)


def make_lockfile() -> Lockfile:
    return Lockfile(
        manifest_digest=f"sha256:{'a' * 64}",
        target="linux/amd64",
        sources={
            "core": ResolvedSource(
                provider="http",
                version="1.0.0",
                source_revision="1.0.0",
                url="https://example.org/server.jar",
                size=42,
                digest=f"sha256:{'b' * 64}",
                target="server.jar",
            )
        },
        runtime=RuntimeLock(image=f"example:1@sha256:{'c' * 64}"),
    )


def test_lockfile_round_trip_is_canonical(tmp_path: Path) -> None:
    path = tmp_path / LOCKFILE_NAME
    original = make_lockfile()

    write_lockfile(path, original)
    loaded = load_lockfile(path)

    assert loaded == original
    assert path.read_bytes() == original.to_bytes()
    assert original.to_bytes().endswith(b"\n")


def test_lockfile_rejects_unpinned_image() -> None:
    content = make_lockfile().to_bytes().replace(
        f'example:1@sha256:{"c" * 64}'.encode(), b"example:latest"
    )

    with pytest.raises(ValidationError, match="pinned"):
        parse_lockfile(content)


def test_lockfile_rejects_credentials() -> None:
    content = make_lockfile().to_bytes().replace(
        b"https://example.org", b"https://user:secret@example.org"
    )

    with pytest.raises(ValidationError, match="credentials"):
        parse_lockfile(content)
