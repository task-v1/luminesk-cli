"""Require one version across the Git tag, project metadata, and CLI."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

from luminesk_cli._version import __version__

RELEASE_TAG_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[1-9][0-9]*)?")


def main(argv: list[str]) -> int:
    if len(argv) != 1 or RELEASE_TAG_RE.fullmatch(argv[0]) is None:
        raise SystemExit(
            "release tag must be vMAJOR.MINOR.PATCH with an optional aN, bN, or rcN"
        )

    tag_version = argv[0].removeprefix("v")
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project_version = project["project"]["version"]

    if len({tag_version, project_version, __version__}) != 1:
        raise SystemExit(
            f"version mismatch: tag={tag_version}, project={project_version}, "
            f"runtime={__version__}"
        )

    print(f"Verified release version {tag_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
