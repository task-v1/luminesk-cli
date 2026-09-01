from __future__ import annotations

import shutil
from typing import Any

from luminesk_cli.cli.commands.common import emit


def run(namespace: Any) -> int:
    docker = shutil.which("docker")
    checks = [
        {
            "component": "docker",
            "available": docker is not None,
            "requiredFor": "runtime and mutable image resolution",
        },
    ]
    lines = [
        f"{item['component']}: {'ok' if item['available'] else 'missing'} — {item['requiredFor']}"
        for item in checks
    ]
    emit(namespace, {"checks": checks}, "\n".join(lines))
    return 0
