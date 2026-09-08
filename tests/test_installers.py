from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

INSTALLER_ASSETS = {
    "luminesk_cli-linux-amd64",
    "luminesk_cli-linux-arm64",
    "luminesk_cli-darwin-amd64",
    "luminesk_cli-darwin-arm64",
    "luminesk_cli-windows-amd64.exe",
    "luminesk_cli-windows-arm64.exe",
}
BUNDLE_ASSETS = {
    "luminesk-linux-amd64.zip",
    "luminesk-linux-arm64.zip",
    "luminesk-macos-amd64.zip",
    "luminesk-macos-arm64.zip",
    "luminesk-windows-amd64.zip",
    "luminesk-windows-arm64.zip",
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_one_line_installers_fail_closed() -> None:
    shell = (REPOSITORY_ROOT / "assets/install.sh").read_text(encoding="utf-8")
    powershell = (REPOSITORY_ROOT / "assets/install.ps1").read_text(encoding="utf-8")

    assert "Release asset has no valid SHA-256 digest" in shell
    assert "sha256sum or shasum is required" in shell
    assert "releases/download/$REMOTE_TAG/$BINARY_NAME" in shell
    assert "Warning: Could not verify checksum" not in shell
    assert "Release asset has no valid SHA-256 digest" in powershell
    assert "$targetAsset.browser_download_url" in powershell
    metadata_block = powershell.split("# Fetch release info from GitHub API", 1)[1]
    metadata_block = metadata_block.split("$NEEDS_UPDATE", 1)[0]
    assert "} catch {}" not in metadata_block


def test_release_matrix_matches_installer_assets() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/release-pypi.yml").read_text(
        encoding="utf-8"
    )

    for name in INSTALLER_ASSETS:
        workflow_name = name.removesuffix(".exe")
        assert f"installer_asset: {workflow_name}" in workflow
    assert workflow.count("--collect-all platformdirs") == 2


def test_wheel_verifier_parses_dependency_requirements(tmp_path: Path) -> None:
    wheel = tmp_path / "luminesk_cli-2.0.2-py3-none-any.whl"
    metadata = """\
Metadata-Version: 2.4
Name: luminesk-cli
Version: 2.0.2
Requires-Dist: rich>=15.0.0
Requires-Dist: platformdirs[tests] >= 4.10.0; python_version >= "3.13"
"""
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("luminesk_cli/__init__.py", "")
        archive.writestr("luminesk_cli-2.0.2.dist-info/METADATA", metadata)
    command = [
        sys.executable,
        str(REPOSITORY_ROOT / "scripts/verify_wheel.py"),
        str(wheel),
    ]

    accepted = subprocess.run(command, check=False, capture_output=True, text=True)
    assert accepted.returncode == 0, accepted.stderr

    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("luminesk_cli/__init__.py", "")
        archive.writestr(
            "luminesk_cli-2.0.2.dist-info/METADATA",
            metadata + "Requires-Dist: cyclopts>=3.0\n",
        )
    rejected = subprocess.run(command, check=False, capture_output=True, text=True)
    assert rejected.returncode != 0
    assert "cyclopts" in rejected.stderr


def test_release_asset_verifier_accepts_only_complete_hashed_set(
    tmp_path: Path,
) -> None:
    names = (
        INSTALLER_ASSETS
        | BUNDLE_ASSETS
        | {
            "luminesk-cli.cdx.json",
            "luminesk_cli-2.0.2-py3-none-any.whl",
            "luminesk_cli-2.0.2.tar.gz",
        }
    )
    for name in names:
        (tmp_path / name).write_bytes(f"fixture:{name}".encode())
    sums = "".join(
        f"{hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()}  {name}\n"
        for name in sorted(names)
    )
    (tmp_path / "SHA256SUMS").write_text(sums, encoding="ascii")
    command = [
        sys.executable,
        str(REPOSITORY_ROOT / "scripts/verify_release_assets.py"),
        str(tmp_path),
    ]

    valid = subprocess.run(command, check=False, capture_output=True, text=True)
    assert valid.returncode == 0, valid.stderr

    (tmp_path / "luminesk_cli-linux-amd64").unlink()
    invalid = subprocess.run(command, check=False, capture_output=True, text=True)
    assert invalid.returncode != 0
    assert "missing" in invalid.stderr
