"""Release-blocking acceptance test against the published official catalog."""

from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from luminesk_cli.cli.entry import main as cli_main
from luminesk_cli.infrastructure.state import load_state


def _invoke(arguments: list[str]) -> dict[str, Any]:
    output = io.StringIO()
    with redirect_stdout(output):
        code = cli_main([*arguments, "--json", "--non-interactive"])
    rendered = output.getvalue()
    try:
        payload = json.loads(rendered)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"command did not emit one JSON document: {arguments}: {rendered!r}"
        ) from exc
    if code != 0 or payload.get("ok") is not True:
        raise SystemExit(f"command failed ({code}): {arguments}: {payload}")
    return payload


def main_entry() -> int:
    with tempfile.TemporaryDirectory(prefix="luminesk-catalog-acceptance-") as name:
        root = Path(name)
        instance = root / "paper-instance"
        os.environ["XDG_CACHE_HOME"] = str(root / "cache")
        os.environ["XDG_CONFIG_HOME"] = str(root / "config")
        runtime_uid = os.getuid()
        runtime_gid = os.getgid()

        try:
            update = _invoke(["catalog", "update"])
            search = _invoke(["search", "paper", "--edition", "java"])
            if not any(item["name"] == "paper" for item in search["recipes"]):
                raise SystemExit("official catalog search did not return PaperMC")
            info = _invoke(["info", "paper"])
            if info["recipe"]["sourceTypes"] != ["paper"]:
                raise SystemExit("PaperMC catalog metadata has an unexpected source")
            _invoke(
                [
                    "install",
                    "paper",
                    "--dir",
                    str(instance),
                    "--set",
                    "eula=true",
                    "--set",
                    f"runtime_uid={runtime_uid}",
                    "--set",
                    f"runtime_gid={runtime_gid}",
                    "--yes",
                ]
            )
            _invoke(["start", "--dir", str(instance)])
            _invoke(["validate", "--dir", str(instance), "--instance"])
            _invoke(["stop", "--dir", str(instance)])
        finally:
            state = load_state(instance)
            if state is not None and state.runtime.container_id:
                subprocess.run(
                    ["docker", "rm", "--force", state.runtime.container_id],
                    check=False,
                    capture_output=True,
                    shell=False,
                )

        print(
            "Official catalog acceptance passed: "
            f"{update['revision'][:12]} → PaperMC install/start/validate/stop."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())
