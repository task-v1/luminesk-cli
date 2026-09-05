from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY_ROOT / "scripts/check_release_source.py"


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_release_source_must_be_reachable_from_default_branch(tmp_path: Path) -> None:
    _git(tmp_path, "init", "--initial-branch=main")
    _git(tmp_path, "config", "user.name", "Release Test")
    _git(tmp_path, "config", "user.email", "release@example.invalid")
    marker = tmp_path / "marker"
    marker.write_text("main\n", encoding="utf-8")
    _git(tmp_path, "add", "marker")
    _git(tmp_path, "commit", "-m", "main")
    main_commit = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", main_commit)
    command = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(tmp_path),
        "--default-branch",
        "main",
    ]

    accepted = subprocess.run(command, check=False, capture_output=True, text=True)
    assert accepted.returncode == 0, accepted.stderr

    _git(tmp_path, "switch", "-c", "release-candidate")
    marker.write_text("diverged\n", encoding="utf-8")
    _git(tmp_path, "commit", "-am", "diverged")
    rejected = subprocess.run(command, check=False, capture_output=True, text=True)
    assert rejected.returncode != 0
    assert "not reachable from origin/main" in rejected.stderr
