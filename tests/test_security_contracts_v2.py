from __future__ import annotations

import stat
import warnings
import zipfile
from pathlib import Path

import pytest

from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.domain.package import PackageFile, PackageMetadata
from luminesk_cli.domain.primitives import safe_relative_path, sha256_digest
from luminesk_cli.infrastructure.package import verify_package
from luminesk_cli.infrastructure.security.archive import extract_archive


@pytest.mark.parametrize(
    "value",
    [
        "./server.jar",
        "plugins//server.jar",
        "plugins\\server.jar",
        "server.jar/",
        "CON",
        "plugins/NUL.txt",
        "server.jar ",
        "server\x1f.jar",
    ],
)
def test_package_paths_must_be_canonical_and_portable(value: str) -> None:
    with pytest.raises(ValidationError):
        safe_relative_path(value, "fixture.path")


def test_package_verifier_rejects_duplicate_payload_member(tmp_path: Path) -> None:
    content = b"server"
    metadata = PackageMetadata(
        name="fixture",
        version="2.0.0",
        manifest_digest=f"sha256:{'a' * 64}",
        lock_digest=f"sha256:{'b' * 64}",
        target="linux/amd64",
        files=(
            PackageFile(
                path="server.jar",
                type="file",
                mode=0o644,
                size=len(content),
                digest=sha256_digest(content),
                ownership="managed",
            ),
        ),
    )
    package = tmp_path / "duplicate.neskpkg"

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("metadata.json", metadata.to_bytes())
        archive.writestr("payload/server.jar", content)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            archive.writestr("payload/server.jar", content)

    with pytest.raises(SecurityError, match="duplicate"):
        verify_package(package)


def test_zip_special_file_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "special.zip"
    member = zipfile.ZipInfo("device")
    member.create_system = 3
    member.external_attr = (stat.S_IFCHR | 0o600) << 16

    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(member, b"")

    with pytest.raises(SecurityError, match="special"):
        extract_archive(archive, tmp_path / "output")
