"""Create a deterministic ZIP wrapper around a platform onedir bundle."""

from __future__ import annotations

import stat
import sys
import zipfile
from pathlib import Path

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: archive_bundle.py SOURCE_DIR OUTPUT.zip")

    source = Path(argv[0]).resolve()
    output = Path(argv[1]).resolve()

    if not source.is_dir() or output.suffix.lower() != ".zip":
        raise SystemExit("source must be a directory and output must end in .zip")

    output.parent.mkdir(parents=True, exist_ok=True)
    paths = sorted(
        (path for path in source.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(source).as_posix(),
    )

    if not paths:
        raise SystemExit("source bundle is empty")

    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in paths:
            resolved = path.resolve()

            if not resolved.is_relative_to(source):
                raise SystemExit(f"bundle link escapes source directory: {path}")

            relative = path.relative_to(source).as_posix()
            executable = bool(path.stat().st_mode & 0o111)
            mode = 0o755 if executable else 0o644
            info = zipfile.ZipInfo(f"{source.name}/{relative}", ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | mode) << 16

            with path.open("rb") as input_file, archive.open(info, "w") as output_file:
                while chunk := input_file.read(256 * 1024):
                    output_file.write(chunk)

    print(f"Created {output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
