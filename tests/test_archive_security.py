from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.infrastructure.security.archive import extract_archive


def test_zip_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "malicious.zip"

    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.txt", b"escaped")

    with pytest.raises(ValidationError):
        extract_archive(archive, tmp_path / "output")

    assert not (tmp_path / "escape.txt").exists()


def test_tar_symlink_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "malicious.tar"

    with tarfile.open(archive, "w") as handle:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        handle.addfile(link)

    with pytest.raises(SecurityError, match="links"):
        extract_archive(archive, tmp_path / "output")


def test_safe_tar_is_extracted(tmp_path: Path) -> None:
    archive = tmp_path / "safe.tar.gz"
    content = b"server artifact"

    with tarfile.open(archive, "w:gz") as handle:
        item = tarfile.TarInfo("bin/server")
        item.size = len(content)
        handle.addfile(item, io.BytesIO(content))

    files = extract_archive(archive, tmp_path / "output")

    assert len(files) == 1
    assert files[0].read_bytes() == content
