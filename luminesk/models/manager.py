from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from luminesk.core.config import ManagedServer


class ServerManagerError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class ServerRuntimeView:
    server: ManagedServer
    status: str
    pid: int | None
    loop_enabled: bool
    docker_container_name: str | None
    uptime: timedelta | None
    last_started_at: datetime | None
    last_stopped_at: datetime | None
    last_exit_code: int | None


@dataclass(slots=True, frozen=True)
class ResolvedServerTarget:
    server: ManagedServer
    value: str


@dataclass(slots=True, frozen=True)
class ServerSignalResult:
    target: ResolvedServerTarget
    signal_name: str
    server_pid: int | None
    loop_active: bool
    signaled_server: bool


@dataclass(slots=True, frozen=True)
class DownloadedCore:
    executable_path: Path
    hash: str


@dataclass(slots=True, frozen=True)
class CachedCorePaths:
    cache_directory: Path
    executable_path: Path
    metadata_path: Path
