"""Stable import and startup budgets for the cheap CLI paths."""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time

FORBIDDEN = {"filelock", "httpx", "platformdirs", "sqlite3"}
SAMPLES = 20


def _median(argv: list[str]) -> float:
    samples = []

    for _ in range(SAMPLES):
        started = time.perf_counter()
        result = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        samples.append(time.perf_counter() - started)

        if result.returncode != 0:
            raise SystemExit(f"cold-path command failed: {argv}")

    return statistics.median(samples)


def _imports(arguments: list[str]) -> set[str]:
    script = (
        "import json,sys; from luminesk_cli.cli.entry import main; "
        f"args={arguments!r}; "
        "code=0; "
        "\ntry: code=main(args)\n"
        "except SystemExit as exc: code=exc.code or 0\n"
        "print('__LUMINESK_MODULES__'+json.dumps(sorted(sys.modules))); "
        "raise SystemExit(code)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )

    if result.returncode != 0:
        raise SystemExit(result.stderr or "cold import probe failed")

    marker = next(
        (
            line.removeprefix("__LUMINESK_MODULES__")
            for line in result.stdout.splitlines()
            if line.startswith("__LUMINESK_MODULES__")
        ),
        None,
    )

    if marker is None:
        raise SystemExit("cold import probe did not return module metadata")

    modules = json.loads(marker)
    return {name.split(".", 1)[0] for name in modules}


def main() -> int:
    for arguments in (["--version"], ["--help"]):
        imported = _imports(arguments)
        unexpected = imported & FORBIDDEN

        if unexpected:
            raise SystemExit(
                f"{arguments[0]} imported forbidden modules: {sorted(unexpected)}"
            )

    baseline = _median([sys.executable, "-c", "pass"])
    version = _median([sys.executable, "-m", "luminesk_cli", "--version"])
    help_time = _median([sys.executable, "-m", "luminesk_cli", "--help"])
    version_limit = max(baseline * 2.5, baseline + 0.050)
    help_limit = max(baseline * 5.0, baseline + 0.200)

    if version > version_limit:
        raise SystemExit(f"version startup {version:.4f}s exceeds {version_limit:.4f}s")

    if help_time > help_limit:
        raise SystemExit(f"help startup {help_time:.4f}s exceeds {help_limit:.4f}s")

    print(
        f"Cold path p50: empty={baseline:.4f}s, version={version:.4f}s, "
        f"help={help_time:.4f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
