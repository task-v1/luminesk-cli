from __future__ import annotations

import shutil
import subprocess
from typing import Any

from luminesk_cli.cli.commands.common import emit
from luminesk_cli.domain.errors import RuntimeOperationError


def run(namespace: Any) -> int:
    docker = shutil.which("docker")
    check: dict[str, Any] = {
        "component": "docker",
        "available": docker is not None,
        "daemonReachable": False,
        "requiredFor": "runtime and mutable image resolution",
    }
    checks = [check]
    if docker is None:
        raise RuntimeOperationError("Docker CLI is not available", checks=checks)
    try:
        result = subprocess.run(
            [docker, "version", "--format", "{{json .}}"],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeOperationError(
            "Docker daemon health check failed", checks=checks
        ) from exc
    if result.returncode != 0:
        raise RuntimeOperationError(
            "Docker daemon is not reachable",
            checks=checks,
            stderr=result.stderr[-4000:],
        )
    check["daemonReachable"] = True
    check["version"] = result.stdout.strip()
    lines = [
        f"{item['component']}: ok — CLI available and daemon reachable"
        for item in checks
    ]
    emit(namespace, {"checks": checks}, "\n".join(lines))
    return 0
