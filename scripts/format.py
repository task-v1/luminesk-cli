"""Apply or verify the repository's single Ruff formatting policy."""

from __future__ import annotations

import subprocess
import sys


def main(argv: list[str]) -> int:
    fix = "--fix" in argv
    paths = [argument for argument in argv if argument != "--fix"] or ["."]
    command = ["ruff", "format"]
    if not fix:
        command.append("--check")
    command.extend(paths)
    result = subprocess.run(command, check=False, shell=False)
    if result.returncode == 0:
        action = "Formatted" if fix else "Verified formatting for"
        print(f"{action} {len(paths)} path(s).")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
