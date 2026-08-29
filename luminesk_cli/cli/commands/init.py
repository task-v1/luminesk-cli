from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from luminesk_cli.cli.commands.common import emit
from luminesk_cli.domain.errors import ConflictError, ValidationError
from luminesk_cli.domain.manifest import MANIFEST_NAME

SKELETON = '''\
manifest_version = 1

[package]
name = "{name}"
version = "0.1.0"
description = "A Nesk server recipe"
platforms = ["linux/amd64", "linux/arm64"]

[[sources]]
id = "core"
provider = "http"
url = "https://example.invalid/server.jar"
version = "1.0.0"
target = "server.jar"
max_size = 536870912

[runtime]
driver = "docker"
image = "eclipse-temurin:21-jre"
command = ["java", "-jar", "server.jar"]
workdir = "/server"
read_only_root = true

[[runtime.mounts]]
source = "."
target = "/server"
mode = "rw"

[[checks]]
id = "core-present"
phase = "post-build"
kind = "file"
path = "server.jar"

[update]
strategy = "transactional"
backup = ["worlds", "server.properties", "plugins"]
retain_backups = 3
rollback_on_failure = true

[permissions]
build = false
host_commands = false
'''


def run(namespace: Any) -> int:
    root = Path(namespace.dir).expanduser().resolve()
    path = root / MANIFEST_NAME

    if path.exists():
        raise ConflictError(f"{path} already exists")

    name = namespace.name or root.name.lower().replace(" ", "-")

    if re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name) is None:
        raise ValidationError("recipe name must be a lowercase package identifier")

    root.mkdir(parents=True, exist_ok=True)
    path.write_text(SKELETON.format(name=name), encoding="utf-8", newline="\n")
    emit(namespace, {"manifest": str(path)}, f"Created {path}")
    return 0
