"""Idempotent, data-preserving Nesk 1.x to 2.0 migration."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from luminesk_cli._version import __version__
from luminesk_cli.compatibility_recipes import (
    COMPATIBILITY_CORE_IDS,
    recipe_root,
)
from luminesk_cli.domain.errors import (
    ConflictError,
    RuntimeOperationError,
    ValidationError,
)
from luminesk_cli.domain.instance import (
    InstanceState,
    OwnershipEntry,
    OwnershipLedger,
    RecipeState,
    RuntimeState,
)
from luminesk_cli.domain.lockfile import (
    LOCKFILE_NAME,
    Lockfile,
    RecipeLock,
    ResolvedSource,
    RuntimeLock,
    write_lockfile,
)
from luminesk_cli.domain.manifest import MANIFEST_NAME, parse_manifest
from luminesk_cli.domain.primitives import sha256_digest
from luminesk_cli.infrastructure.cache import digest_file
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.state import (
    InstanceIndex,
    atomic_write,
    load_state,
    state_directory,
    write_ownership,
    write_state,
)

MAX_LEGACY_METADATA_SIZE = 1024 * 1024


@dataclass(slots=True, frozen=True)
class LegacyInstance:
    root: Path
    tag: str
    name: str
    core_id: str
    executable_name: str
    core_hash: str | None
    config_file: str
    port_way: str
    runtime_image: str
    memory_limit: str
    running: bool
    raw_metadata: bytes


@dataclass(slots=True, frozen=True)
class MigrationReport:
    root: str
    core_id: str
    manifest: str
    lockfile: str
    files_owned: int
    warnings: tuple[str, ...]
    dry_run: bool
    already_migrated: bool = False


class V1Migrator:
    def __init__(
        self,
        *,
        legacy_database: Path | None = None,
        index: InstanceIndex | None = None,
        image_resolver: OciImageResolver | None = None,
    ) -> None:
        self.legacy_database = legacy_database
        self.index = index
        self.image_resolver = image_resolver or OciImageResolver()

    def migrate(
        self,
        identifier: str | Path,
        *,
        dry_run: bool = False,
    ) -> MigrationReport:
        legacy, warnings = self._load_legacy(identifier)
        existing_state = load_state(legacy.root)

        if existing_state is not None:
            return MigrationReport(
                root=str(legacy.root),
                core_id=legacy.core_id,
                manifest=str(legacy.root / MANIFEST_NAME),
                lockfile=str(legacy.root / LOCKFILE_NAME),
                files_owned=len(
                    json.loads(
                        (
                            state_directory(legacy.root) / "ownership.json"
                        ).read_text(encoding="utf-8")
                    ).get("files", {})
                ),
                warnings=("instance is already migrated",),
                dry_run=dry_run,
                already_migrated=True,
            )

        if legacy.running:
            raise RuntimeOperationError("a running Nesk 1.x instance cannot be migrated")

        if legacy.core_id not in COMPATIBILITY_CORE_IDS:
            raise ValidationError(
                f"no migration recipe exists for legacy core {legacy.core_id}"
            )

        recipe_root(legacy.core_id)
        executable = (legacy.root / legacy.executable_name).resolve()

        if not executable.is_relative_to(legacy.root) or not executable.is_file():
            raise ValidationError(
                "legacy executable is missing or outside the instance",
                path=str(executable),
            )

        executable_digest, executable_size = digest_file(executable)

        if legacy.core_hash is None or not _legacy_hash_matches(
            legacy.core_hash, executable_digest
        ):
            warnings.append(
                "legacy core_hash was not a verified SHA-256 content digest; "
                "the current executable was hashed locally"
            )

        image = self.image_resolver.resolve(
            legacy.runtime_image,
            allow_pull=not dry_run,
        )
        port = _legacy_port(legacy)
        manifest_content = _manifest_bytes(legacy, port)
        manifest = parse_manifest(manifest_content, source=str(legacy.root / MANIFEST_NAME))
        lockfile = Lockfile(
            manifest_digest=manifest.digest,
            target=_migration_target(),
            sources={
                "core": ResolvedSource(
                    provider="local-file",
                    version="migrated-1.x",
                    source_revision=(
                        legacy.core_hash or "unverified-migrated"
                    ),
                    url=f"local:{legacy.executable_name}",
                    size=executable_size,
                    digest=executable_digest,
                    target=legacy.executable_name,
                )
            },
            runtime=RuntimeLock(image=image),
            recipe=RecipeLock(
                source=f"builtin:{legacy.core_id}",
                revision=__version__,
                tracking=False,
            ),
        )
        ledger = _migration_ownership(legacy, executable_digest)

        if dry_run:
            return MigrationReport(
                root=str(legacy.root),
                core_id=legacy.core_id,
                manifest=str(legacy.root / MANIFEST_NAME),
                lockfile=str(legacy.root / LOCKFILE_NAME),
                files_owned=len(ledger.files),
                warnings=tuple(warnings),
                dry_run=True,
            )

        manifest_path = legacy.root / MANIFEST_NAME

        if manifest_path.exists() or (legacy.root / LOCKFILE_NAME).exists():
            raise ConflictError(
                "migration will not overwrite an existing manifest or lockfile"
            )

        timestamp = datetime.now(UTC).isoformat()
        package_digest = sha256_digest(
            f"migrated:{executable_digest}:{lockfile.digest}".encode()
        )
        state = InstanceState(
            instance_id=sha256_digest(str(legacy.root).encode()).split(":", 1)[1][:32],
            name=legacy.name,
            tag=legacy.tag,
            root=str(legacy.root),
            applied_lock_digest=lockfile.digest,
            installed_package_digest=package_digest,
            recipe=RecipeState(
                source=f"builtin:{legacy.core_id}", revision=__version__
            ),
            inputs={"port": port, "memory": legacy.memory_limit},
            runtime=RuntimeState(),
            created_at=timestamp,
            updated_at=timestamp,
        )
        backup = (
            state_directory(legacy.root)
            / "backups"
            / f"migration-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        )
        backup.mkdir(parents=True, exist_ok=False)
        atomic_write(backup / "core.json", legacy.raw_metadata)

        try:
            atomic_write(manifest_path, manifest_content)
            write_lockfile(legacy.root / LOCKFILE_NAME, lockfile)
            write_ownership(legacy.root, ledger)
            write_state(legacy.root, state)

            if self.index is not None:
                self.index.register(state)
        except BaseException:
            manifest_path.unlink(missing_ok=True)
            (legacy.root / LOCKFILE_NAME).unlink(missing_ok=True)
            (state_directory(legacy.root) / "state.json").unlink(missing_ok=True)
            (state_directory(legacy.root) / "ownership.json").unlink(missing_ok=True)
            raise

        return MigrationReport(
            root=str(legacy.root),
            core_id=legacy.core_id,
            manifest=str(manifest_path),
            lockfile=str(legacy.root / LOCKFILE_NAME),
            files_owned=len(ledger.files),
            warnings=tuple(warnings),
            dry_run=False,
        )

    def _load_legacy(
        self, identifier: str | Path
    ) -> tuple[LegacyInstance, list[str]]:
        path_candidate = Path(identifier).expanduser()
        database_row = None

        if path_candidate.exists():
            root = path_candidate.resolve()
        else:
            database_row = self._database_row(str(identifier), by_tag=True)

            if database_row is None:
                raise ValidationError(f"legacy instance not found: {identifier}")

            root = Path(database_row[2]).expanduser().resolve()

        metadata_path = root / ".luminesk_cli" / "core.json"

        if not metadata_path.is_file():
            raise ValidationError(f"legacy metadata is missing: {metadata_path}")

        if metadata_path.stat().st_size > MAX_LEGACY_METADATA_SIZE:
            raise ValidationError("legacy metadata exceeds size limit")

        raw = metadata_path.read_bytes()

        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("legacy core.json is invalid") from exc

        if not isinstance(value, dict):
            raise ValidationError("legacy core.json root must be an object")

        warnings = []
        path_row = self._database_row(str(root), by_tag=False)
        database_row = database_row or path_row

        if database_row is not None:
            db_tag, db_name, _, db_core = database_row

            for field, metadata_value, database_value in (
                ("tag", value.get("tag"), db_tag),
                ("name", value.get("name"), db_name),
                ("core_id", value.get("core_id"), db_core),
            ):
                if metadata_value not in {None, database_value}:
                    warnings.append(
                        f"{field} differs between SQLite and core.json; SQLite wins"
                    )

            value.update({"tag": db_tag, "name": db_name, "core_id": db_core})

        runtime = value.get("runtime")
        running = isinstance(runtime, dict) and runtime.get("status") == "running"
        return (
            LegacyInstance(
                root=root,
                tag=_required_legacy_string(value, "tag"),
                name=_required_legacy_string(value, "name"),
                core_id=_required_legacy_string(value, "core_id"),
                executable_name=_required_legacy_string(value, "executable_name"),
                core_hash=(
                    str(value["core_hash"]) if value.get("core_hash") else None
                ),
                config_file=str(value.get("config_file", "server.properties")),
                port_way=str(value.get("port_way", "server-port")),
                runtime_image=str(
                    value.get("runtime_image", "eclipse-temurin:21-jre")
                ),
                memory_limit=str(value.get("memory_limit", "1g")),
                running=running,
                raw_metadata=raw,
            ),
            warnings,
        )

    def _database_row(
        self, value: str, *, by_tag: bool
    ) -> tuple[str, str, str, str] | None:
        if self.legacy_database is None or not self.legacy_database.is_file():
            return None

        column = "tag" if by_tag else "path"

        try:
            with sqlite3.connect(f"file:{self.legacy_database}?mode=ro", uri=True) as connection:
                row = connection.execute(
                    f"SELECT tag, name, path, core_id FROM servers WHERE {column} = ?",  # noqa: S608
                    (value,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise ValidationError(f"cannot read legacy database: {exc}") from exc

        return tuple(row) if row is not None else None  # type: ignore[return-value]


def _required_legacy_string(value: dict[str, Any], key: str) -> str:
    item = value.get(key)

    if not isinstance(item, str) or not item.strip():
        raise ValidationError(f"legacy metadata is missing {key}")

    return item.strip()


def _legacy_hash_matches(value: str, digest: str) -> bool:
    normalized = value.lower().removeprefix("sha256:")
    return bool(re.fullmatch(r"[0-9a-f]{64}", normalized)) and digest == (
        f"sha256:{normalized}"
    )


def _legacy_port(legacy: LegacyInstance) -> int:
    try:
        from luminesk_cli.utils.config_parser import get_server_port

        return get_server_port(legacy.root, legacy.config_file, legacy.port_way)
    except Exception:
        return 19132


def _manifest_bytes(legacy: LegacyInstance, port: int) -> bytes:
    command = _runtime_command(legacy.executable_name)
    quoted_command = ", ".join(json.dumps(item) for item in command)
    package_name = re.sub(r"[^a-z0-9._-]+", "-", legacy.tag.lower()).strip("-._")
    content = f'''\
manifest_version = 1
[package]
name = {json.dumps(package_name or legacy.core_id)}
version = "1.0.0+migrated"
description = "Migrated Nesk 1.x {legacy.core_id} instance"
[inputs.port]
type = "integer"
default = {port}
min = 1
max = 65535
[inputs.memory]
type = "string"
default = {json.dumps(legacy.memory_limit)}
[[sources]]
id = "core"
provider = "local-file"
path = {json.dumps(legacy.executable_name)}
target = {json.dumps(legacy.executable_name)}
integrity = "unverified-migrated"
[runtime]
driver = "docker"
image = {json.dumps(legacy.runtime_image)}
command = [{quoted_command}]
memory = "${{input.memory}}"
[[runtime.mounts]]
source = "."
target = "/server"
mode = "rw"
[[runtime.ports]]
name = "bedrock"
host = "${{input.port}}"
container = "${{input.port}}"
protocol = "udp"
[update]
strategy = "transactional"
backup = ["worlds", "plugins", {json.dumps(legacy.config_file)}]
retain_backups = 3
rollback_on_failure = true
[permissions]
build = false
host_commands = false
'''
    return content.encode("utf-8")


def _runtime_command(executable: str) -> tuple[str, ...]:
    if executable.endswith(".jar"):
        return ("java", "-jar", executable)

    if executable.endswith(".phar"):
        return ("php", executable)

    return (f"./{executable}",)


def _migration_ownership(
    legacy: LegacyInstance,
    executable_digest: str,
) -> OwnershipLedger:
    entries = {
        legacy.executable_name: OwnershipEntry(
            mode="managed", digest=executable_digest
        )
    }
    config = legacy.root / legacy.config_file

    if config.is_file():
        digest, _ = digest_file(config)
        entries[legacy.config_file] = OwnershipEntry(mode="preserve", digest=digest)

    for directory in ("worlds", "plugins"):
        if (legacy.root / directory).is_dir():
            entries[directory] = OwnershipEntry(mode="data", digest=None)

    return OwnershipLedger(entries)


def _migration_target() -> str:
    from luminesk_cli.infrastructure.platform import current_platform

    return current_platform()
