from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from luminesk.utils.docker import DockerLaunchTarget


class ServerLaunchTarget(DockerLaunchTarget, Protocol):
    memory_limit: str
    runtime_image: str


@dataclass(slots=True, frozen=True)
class DetachedLaunchResult:
    container_id: str
    container_name: str
    command: tuple[str, ...]
    attach_command: tuple[str, ...]
    log_path: Path
    memory_limit: str
    runtime_image: str
