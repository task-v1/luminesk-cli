from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from luminesk_cli.cli.commands.common import emit
from luminesk_cli.domain.errors import ConflictError, ValidationError
from luminesk_cli.domain.manifest import MANIFEST_NAME

SKELETON = """\
manifest_version = 1

[package]
name = "{name}"
version = "0.1.0"
display_name = "{name}"
kind = "core"
game = "minecraft"
edition = "java"
summary = "A Minecraft server recipe"
keywords = ["minecraft", "java"]
platforms = ["linux/amd64", "linux/arm64"]

[[sources]]
id = "core"
type = "http"
target = "server.jar"
max_size = 536870912
[sources.options]
url = "https://example.invalid/server.jar"
version = "1.0.0"

[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-jar", "server.jar"]

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
"""


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
