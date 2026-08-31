"""Real Docker smoke test used by the scheduled Luminesk 2.0 E2E workflow."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from luminesk_cli.cli.entry import main
from luminesk_cli.infrastructure.state import load_state

IMAGE = "busybox:1.37"


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )


def main_entry() -> int:
    _run(["docker", "pull", IMAGE])
    inspect = _run(
        [
            "docker",
            "image",
            "inspect",
            IMAGE,
            "--format",
            "{{json .RepoDigests}}",
        ]
    )
    digests = json.loads(inspect.stdout)

    if not isinstance(digests, list) or not digests:
        raise SystemExit("Docker returned no BusyBox repository digest")

    pinned_image = str(digests[0])

    with tempfile.TemporaryDirectory(prefix="luminesk-e2e-") as temporary:
        root = Path(temporary) / "instance"
        root.mkdir()
        os.environ["XDG_CACHE_HOME"] = str(Path(temporary) / "cache")
        os.environ["XDG_CONFIG_HOME"] = str(Path(temporary) / "config")
        (root / "fixture.in").write_bytes(b"luminesk 2.0 e2e")
        (root / "luminesk.toml").write_text(
            f'''\
manifest_version = 1
[package]
name = "docker-e2e"
version = "2.0.0"
[[sources]]
id = "fixture"
provider = "local-file"
path = "fixture.in"
target = "fixture.txt"
[runtime]
driver = "docker"
image = "{pinned_image}"
command = ["sleep", "300"]
run_as = "65534:65534"
read_only_root = true
[[checks]]
id = "alive"
phase = "readiness"
kind = "process-alive"
timeout = 5
''',
            encoding="utf-8",
        )

        try:
            for arguments in (
                ["install", "--dir", str(root), "--json", "--non-interactive"],
                ["start", "--dir", str(root), "--json", "--non-interactive"],
                ["status", "--dir", str(root), "--json", "--non-interactive"],
                ["stop", "--dir", str(root), "--json", "--non-interactive"],
            ):
                if main(arguments) != 0:
                    raise SystemExit(f"Luminesk E2E command failed: {arguments}")
        finally:
            state = load_state(root)

            if state is not None and state.runtime.container_id:
                subprocess.run(
                    ["docker", "rm", "--force", state.runtime.container_id],
                    check=False,
                    capture_output=True,
                    shell=False,
                )

    print("Docker lifecycle E2E passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())
