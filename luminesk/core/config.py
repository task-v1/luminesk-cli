from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from platformdirs import user_cache_dir, user_config_dir

from luminesk.core.messages import DEFAULT_LANGUAGE, normalize_language, t
from luminesk.utils.docker import (
    DEFAULT_DOCKER_MEMORY_LIMIT,
    DEFAULT_FALLBACK_IMAGE,
    normalize_memory_limit,
    normalize_runtime_image,
)

CONFIG_DIR = Path(user_config_dir("luminesk"))
CONFIG_DB_FILE = CONFIG_DIR / "state.sqlite3"
CACHE_DIR = Path(user_cache_dir("luminesk"))
CORE_CACHE_DIR = CACHE_DIR / "cores"

SQLITE_BUSY_TIMEOUT_MS = 30_000

ServerStatus = Literal["running", "stopped"]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ServerRuntime:
    status: ServerStatus = "stopped"
    pid: int | None = None
    loop_enabled: bool = False
    docker_container_id: str | None = None
    docker_container_name: str | None = None
    docker_memory_limit: str | None = None
    last_started_at: datetime | None = None
    last_stopped_at: datetime | None = None
    last_exit_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "pid": self.pid,
            "loop_enabled": self.loop_enabled,
            "docker_container_id": self.docker_container_id,
            "docker_container_name": self.docker_container_name,
            "docker_memory_limit": self.docker_memory_limit,
            "last_started_at": self.last_started_at.isoformat()
            if self.last_started_at
            else None,
            "last_stopped_at": self.last_stopped_at.isoformat()
            if self.last_stopped_at
            else None,
            "last_exit_code": self.last_exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerRuntime:
        last_started_at = data.get("last_started_at")

        if isinstance(last_started_at, str):
            last_started_at = datetime.fromisoformat(last_started_at)

        last_stopped_at = data.get("last_stopped_at")

        if isinstance(last_stopped_at, str):
            last_stopped_at = datetime.fromisoformat(last_stopped_at)

        return cls(
            status=data.get("status", "stopped"),
            pid=data.get("pid"),
            loop_enabled=bool(data.get("loop_enabled", False)),
            docker_container_id=data.get("docker_container_id"),
            docker_container_name=data.get("docker_container_name"),
            docker_memory_limit=data.get("docker_memory_limit"),
            last_started_at=last_started_at,
            last_stopped_at=last_stopped_at,
            last_exit_code=data.get("last_exit_code"),
        )


@dataclass
class ManagedServer:
    name: str
    tag: str
    path: Path
    core_id: str
    executable_name: str
    core_hash: str | None = None
    config_file: str = "server.properties"
    port_way: str = "server-port"
    runtime_image: str = DEFAULT_FALLBACK_IMAGE
    memory_limit: str = DEFAULT_DOCKER_MEMORY_LIMIT
    created_at: datetime = field(default_factory=utc_now)
    runtime: ServerRuntime = field(default_factory=ServerRuntime)

    def __post_init__(self) -> None:
        self.tag = self.tag.strip().lower()

        if not self.tag:
            raise ValueError(t("config.validation.tag_empty"))

        import re

        if not re.match(r"^[a-z0-9\-_.]+$", self.tag):
            raise ValueError(t("config.validation.tag_invalid"))

        for field_name, value in (
            ("name", self.name),
            ("core_id", self.core_id),
            ("executable_name", self.executable_name),
        ):
            if not value.strip():
                raise ValueError(t("config.validation.text_empty"))

        self.name = self.name.strip()
        self.core_id = self.core_id.strip()
        self.executable_name = self.executable_name.strip().replace("\\", "/")
        self.config_file = self.config_file.strip()
        self.port_way = self.port_way.strip()
        self.path = Path(self.path).expanduser().resolve()
        self.memory_limit = normalize_memory_limit(self.memory_limit)
        self.runtime_image = normalize_runtime_image(self.runtime_image)

    @property
    def executable_path(self) -> Path:
        return self.path / self.executable_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tag": self.tag,
            "path": str(self.path),
            "core_id": self.core_id,
            "core_hash": self.core_hash,
            "executable_name": self.executable_name,
            "config_file": self.config_file,
            "port_way": self.port_way,
            "runtime_image": self.runtime_image,
            "memory_limit": self.memory_limit,
            "created_at": self.created_at.isoformat(),
            "runtime": self.runtime.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManagedServer:
        created_at = data.get("created_at")

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = utc_now()

        runtime_data = data.get("runtime")

        if isinstance(runtime_data, dict):
            runtime = ServerRuntime.from_dict(runtime_data)
        else:
            runtime = ServerRuntime()

        return cls(
            name=data["name"],
            tag=data["tag"],
            path=Path(data["path"]),
            core_id=data["core_id"],
            executable_name=data["executable_name"],
            core_hash=data.get("core_hash"),
            config_file=data.get("config_file", "server.properties"),
            port_way=data.get("port_way", "server-port"),
            runtime_image=data.get("runtime_image", DEFAULT_FALLBACK_IMAGE),
            memory_limit=data.get("memory_limit", DEFAULT_DOCKER_MEMORY_LIMIT),
            created_at=created_at,
            runtime=runtime,
        )


@dataclass
class UserConfig:
    language: str = DEFAULT_LANGUAGE
    default_server_path: Path = field(default_factory=lambda: Path("./servers"))
    servers: dict[str, ManagedServer] = field(default_factory=dict)
    db_path: Path = field(default_factory=lambda: CONFIG_DB_FILE)

    _loaded_tags: set[str] = field(default_factory=set, init=False, repr=False)
    _deleted_tags: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        self.language = normalize_language(self.language)
        self.default_server_path = Path(self.default_server_path).expanduser()
        self._loaded_tags = set(self.servers)
        self._deleted_tags = set()

    def save(self) -> None:
        conn = _connect(self.db_path)

        try:
            with _write_transaction(conn):
                _initialize_database(conn)
                _save_settings(conn, self)
                for tag in self._deleted_tags:
                    conn.execute("DELETE FROM servers WHERE tag = ?", (tag,))

                for server in self.servers.values():
                    if server.tag in self._loaded_tags:
                        _upsert_server(conn, server)
                    else:
                        _insert_server(conn, server)

                    try:
                        metadata_dir = server.path / ".luminesk"
                        metadata_dir.mkdir(parents=True, exist_ok=True)
                        metadata_file = metadata_dir / "core.json"
                        import json
                        payload = server.to_dict()
                        metadata_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    except Exception:
                        pass

            self._loaded_tags = set(self.servers)
            self._deleted_tags.clear()
        finally:
            conn.close()

    def register_server(self, server: ManagedServer) -> None:
        self.servers[server.tag] = server
        self._deleted_tags.discard(server.tag)

    def unregister_server(self, tag: str) -> ManagedServer:
        server = self.get_server_by_tag(tag)

        if server is None:
            raise KeyError(t("config.server.not_found", tag=tag))

        deleted_server = self.servers.pop(server.tag)
        self._deleted_tags.add(server.tag)
        return deleted_server

    def get_server_by_tag(self, tag: str) -> ManagedServer | None:
        return self.servers.get(tag.strip().lower())

    def get_server_by_directory(self, directory: Path) -> ManagedServer | None:
        resolved_directory = directory.expanduser().resolve()
        best_match: ManagedServer | None = None

        for server in self.servers.values():
            try:
                if resolved_directory.is_relative_to(server.path):
                    if best_match is None or len(server.path.parts) > len(
                        best_match.path.parts
                    ):
                        best_match = server
            except ValueError:
                continue

        return best_match

    def get_servers(self) -> list[ManagedServer]:
        return sorted(self.servers.values(), key=lambda server: server.tag)

    def mark_server_started(
        self,
        tag: str,
        pid: int | None,
        loop_enabled: bool = False,
        docker_container_id: str | None = None,
        docker_container_name: str | None = None,
        docker_memory_limit: str | None = None,
        started_at: datetime | None = None,
    ) -> ManagedServer:
        server = self._require_server(tag)
        server.runtime.status = "running"
        server.runtime.pid = pid
        server.runtime.loop_enabled = loop_enabled
        server.runtime.docker_container_id = docker_container_id
        server.runtime.docker_container_name = docker_container_name
        server.runtime.docker_memory_limit = docker_memory_limit
        server.runtime.last_started_at = started_at or utc_now()
        server.runtime.last_exit_code = None
        return server

    def mark_server_stopped(
        self,
        tag: str,
        exit_code: int | None,
        preserve_loop: bool = False,
        stopped_at: datetime | None = None,
    ) -> ManagedServer:
        server = self._require_server(tag)
        server.runtime.status = "stopped"
        server.runtime.pid = None

        if not preserve_loop:
            server.runtime.loop_enabled = False

        server.runtime.docker_container_id = None
        server.runtime.docker_container_name = None
        server.runtime.docker_memory_limit = None
        server.runtime.last_stopped_at = stopped_at or utc_now()
        server.runtime.last_exit_code = exit_code
        return server

    def _require_server(self, tag: str) -> ManagedServer:
        server = self.get_server_by_tag(tag)

        if server is None:
            raise KeyError(t("config.server.not_found", tag=tag))

        return server

    @classmethod
    def load(cls) -> UserConfig:
        conn = _connect(CONFIG_DB_FILE)

        try:
            _initialize_database(conn)
            return _load_config_from_database(conn)
        finally:
            conn.close()

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "default_server_path": str(self.default_server_path),
            "servers": {tag: srv.to_dict() for tag, srv in self.servers.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserConfig:
        servers_data = data.get("servers", {})
        servers = {}

        if isinstance(servers_data, dict):
            for tag, srv_data in servers_data.items():
                servers[tag] = ManagedServer.from_dict(srv_data)

        return cls(
            language=data.get("language", DEFAULT_LANGUAGE),
            default_server_path=Path(data.get("default_server_path", "./servers")),
            servers=servers,
            db_path=CONFIG_DB_FILE,
        )


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        db_path,
        timeout=SQLITE_BUSY_TIMEOUT_MS / 1000,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _initialize_database(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
		CREATE TABLE IF NOT EXISTS settings (
			key TEXT PRIMARY KEY,
			value TEXT NOT NULL
		)
		"""
    )
    conn.execute(
        """
		CREATE TABLE IF NOT EXISTS servers (
			tag TEXT PRIMARY KEY,
			name TEXT NOT NULL,
			path TEXT NOT NULL,
			core_id TEXT NOT NULL
		)
		"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_servers_path ON servers(path)")


@contextmanager
def _write_transaction(conn: sqlite3.Connection) -> Iterator[None]:
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        if _is_sqlite_lock_error(exc):
            raise RuntimeError(t("config.sqlite.lock_timeout")) from exc
        raise

    try:
        yield
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def _is_sqlite_lock_error(error: sqlite3.OperationalError) -> bool:
    message = str(error).lower()
    return "locked" in message or "busy" in message


def _create_fallback_server(name: str, tag: str, path: Path, core_id: str = "unknown") -> ManagedServer:
    return ManagedServer(
        name=name,
        tag=tag,
        path=path,
        core_id=core_id,
        executable_name="server.jar",
        core_hash=None,
        config_file="server.properties",
        port_way="server-port",
        runtime_image=DEFAULT_FALLBACK_IMAGE,
        memory_limit=DEFAULT_DOCKER_MEMORY_LIMIT,
        created_at=utc_now(),
        runtime=ServerRuntime()
    )


def _load_config_from_database(conn: sqlite3.Connection) -> UserConfig:
    settings = {
        row["key"]: row["value"]
        for row in conn.execute("SELECT key, value FROM settings")
    }

    servers = {}

    for row in conn.execute("SELECT tag, name, path, core_id FROM servers ORDER BY tag"):
        tag = row["tag"]
        name = row["name"]
        path_str = row["path"]
        core_id = row["core_id"]
        path = Path(path_str)

        # Load core.json
        metadata_file = path / ".luminesk" / "core.json"
        server_data = None
        if metadata_file.is_file():
            try:
                import json
                server_data = json.loads(metadata_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if server_data and isinstance(server_data, dict):
            # Override database columns just in case
            server_data["tag"] = tag
            server_data["name"] = name
            server_data["path"] = path_str

            if "core_id" not in server_data or not server_data["core_id"] or server_data["core_id"] == "unknown":
                server_data["core_id"] = core_id

            try:
                server = ManagedServer.from_dict(server_data)
            except Exception:
                server = _create_fallback_server(name, tag, path, core_id)
        else:
            server = _create_fallback_server(name, tag, path, core_id)

        servers[tag] = server

    return UserConfig(
        language=settings.get("language", DEFAULT_LANGUAGE),
        default_server_path=Path(settings.get("default_server_path", "./servers")),
        servers=servers,
        db_path=CONFIG_DB_FILE,
    )


def _save_settings(conn: sqlite3.Connection, config: UserConfig) -> None:
    conn.executemany(
        """
		INSERT INTO settings(key, value)
		VALUES(?, ?)
		ON CONFLICT(key) DO UPDATE SET value = excluded.value
		""",
        [
            ("language", config.language),
            ("default_server_path", str(config.default_server_path)),
        ],
    )


def _insert_server(conn: sqlite3.Connection, server: ManagedServer) -> None:
    try:
        conn.execute(
            "INSERT INTO servers(tag, name, path, core_id) VALUES(?, ?, ?, ?)",
            (server.tag, server.name, str(server.path), server.core_id),
        )
    except sqlite3.IntegrityError as exc:
        raise RuntimeError(t("config.sqlite.server_conflict", tag=server.tag)) from exc


def _upsert_server(conn: sqlite3.Connection, server: ManagedServer) -> None:
    conn.execute(
        """
		INSERT INTO servers(tag, name, path, core_id)
		VALUES(?, ?, ?, ?)
		ON CONFLICT(tag) DO UPDATE SET
			name = excluded.name,
			path = excluded.path,
			core_id = excluded.core_id
		""",
        (server.tag, server.name, str(server.path), server.core_id),
    )

