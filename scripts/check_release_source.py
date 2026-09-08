"""Require every release candidate SHA to come from the default branch."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

BRANCH_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._/-]*[A-Za-z0-9])?$")


def _git(
    root: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=check,
        capture_output=True,
        text=True,
        shell=False,
    )


def verify(root: Path, default_branch: str) -> str:
    if BRANCH_RE.fullmatch(default_branch) is None or ".." in default_branch:
        raise SystemExit("default branch name is invalid")
    remote_ref = f"refs/remotes/origin/{default_branch}"
    candidate = _git(root, "rev-parse", "HEAD").stdout.strip()
    branch = _git(root, "rev-parse", "--verify", remote_ref).stdout.strip()
    ancestry = _git(
        root,
        "merge-base",
        "--is-ancestor",
        candidate,
        branch,
        check=False,
    )
    if ancestry.returncode != 0:
        raise SystemExit(
            f"release candidate {candidate} is not reachable from "
            f"origin/{default_branch} ({branch})"
        )
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    candidate = verify(arguments.root.resolve(), arguments.default_branch)
    print(
        f"Verified release candidate {candidate} is reachable from "
        f"origin/{arguments.default_branch}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
