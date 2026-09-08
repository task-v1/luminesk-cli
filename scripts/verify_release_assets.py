"""Verify the exact release asset set consumed by one-line installers."""

from __future__ import annotations

import hashlib
import re
import sys
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
CHECKSUM_RE = re.compile(r"^([0-9a-f]{64}) [ *]([^/\\]+)$")


def verify(root: Path) -> None:
    if not root.is_dir() or root.is_symlink():
        raise SystemExit(f"release asset directory is invalid: {root}")
    paths = sorted(root.iterdir(), key=lambda path: path.name)
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"release asset must be a non-empty regular file: {path}")
    names = {path.name for path in paths}
    required = INSTALLER_ASSETS | BUNDLE_ASSETS | {"luminesk-cli.cdx.json"}
    missing = sorted(required - names)
    if missing:
        raise SystemExit(f"release assets are missing: {', '.join(missing)}")

    wheels = sorted(name for name in names if name.endswith(".whl"))
    source_distributions = sorted(
        name
        for name in names
        if name.startswith("luminesk_cli-") and name.endswith(".tar.gz")
    )
    if len(wheels) != 1 or len(source_distributions) != 1:
        raise SystemExit(
            "release assets require exactly one wheel and source distribution"
        )
    allowed = required | set(wheels) | set(source_distributions) | {"SHA256SUMS"}
    unexpected = sorted(names - allowed)
    if unexpected:
        raise SystemExit(f"unexpected release assets: {', '.join(unexpected)}")

    checksum_path = root / "SHA256SUMS"
    checksums: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        match = CHECKSUM_RE.fullmatch(line)
        if match is None or match.group(2) in checksums:
            raise SystemExit("SHA256SUMS is malformed or contains duplicate entries")
        checksums[match.group(2)] = match.group(1)
    expected_names = names - {"SHA256SUMS"}
    if set(checksums) != expected_names:
        raise SystemExit("SHA256SUMS does not cover the exact release asset set")
    for name in sorted(expected_names):
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if checksums[name] != actual:
            raise SystemExit(f"release asset checksum mismatch: {name}")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        raise SystemExit("usage: verify_release_assets.py DIRECTORY")
    root = Path(argv[0]).resolve()
    verify(root)
    print(
        f"Verified {len(INSTALLER_ASSETS)} installer binaries, "
        f"{len(BUNDLE_ASSETS)} bundles, Python artifacts, SBOM, and checksums."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
