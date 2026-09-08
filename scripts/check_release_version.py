"""Require one version across the Git tag, project metadata, and CLI."""

from __future__ import annotations

import re
import runpy
import sys
import tomllib
from pathlib import Path

RELEASE_TAG_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[1-9][0-9]*)?")


def main(argv: list[str]) -> int:
    if len(argv) != 1 or RELEASE_TAG_RE.fullmatch(argv[0]) is None:
        raise SystemExit(
            "release tag must be vMAJOR.MINOR.PATCH with an optional aN, bN, or rcN"
        )

    tag_version = argv[0].removeprefix("v")
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project_version = project["project"]["version"]
    runtime = runpy.run_path("luminesk_cli/_version.py")
    runtime_version = runtime.get("__version__")

    if len({tag_version, project_version, runtime_version}) != 1:
        raise SystemExit(
            f"version mismatch: tag={tag_version}, project={project_version}, "
            f"runtime={runtime_version}"
        )

    print(f"Verified release version {tag_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
