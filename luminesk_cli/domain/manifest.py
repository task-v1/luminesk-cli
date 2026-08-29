"""Strict TOML schema v1 loader for ``luminesk.toml``."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.primitives import (
    PACKAGE_NAME_RE,
    PLATFORM_RE,
    SEMVER_RE,
    fail,
    optional_string,
    read_bounded_utf8,
    reject_unknown,
    require_array,
    require_bool,
    require_int,
    require_keys,
    require_string,
    require_table,
    safe_relative_path,
    sha256_digest,
    validate_https_url,
)

MANIFEST_NAME = "luminesk.toml"
MAX_MANIFEST_SIZE = 1024 * 1024
SOURCE_PROVIDERS = frozenset(
    {"github-release", "maven", "jenkins", "http", "local-file"}
)
FILE_MODES = frozenset({"managed", "preserve", "generated", "data"})
CHECK_PHASES = frozenset({"post-build", "post-install", "readiness"})
CHECK_KINDS = frozenset(
    {"file", "process-alive", "log-regex", "tcp", "command"}
)


@dataclass(slots=True, frozen=True)
class Repository:
    url: str


@dataclass(slots=True, frozen=True)
class Package:
    name: str
    version: str
    description: str = ""
    license: str | None = None
    authors: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    repository: Repository | None = None


@dataclass(slots=True, frozen=True)
class InputSpec:
    name: str
    type: Literal["string", "integer", "boolean"]
    default: str | int | bool | None = None
    prompt: str | None = None
    minimum: int | None = None
    maximum: int | None = None
    pattern: str | None = None
    required: bool = False
    secret: bool = False


@dataclass(slots=True, frozen=True)
class SourceSpec:
    id: str
    provider: str
    target: str
    repository: str | None = None
    url: str | None = None
    version: str | None = None
    channel: str = "stable"
    asset: str | None = None
    group: str | None = None
    artifact: str | None = None
    packaging: str | None = None
    classifier: str | None = None
    job: str | None = None
    build: str | int | None = None
    path: str | None = None
    max_size: int = 536_870_912
    update: str = "pinned"
    integrity: str = "sha256-required"
    extract: bool = False
    allow_http: bool = False
    allow_private_network: bool = False
    platforms: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class FileSpec:
    source: str
    target: str
    mode: Literal["managed", "preserve", "generated", "data"] = "managed"
    template: bool = False
    executable: bool = False


@dataclass(slots=True, frozen=True)
class RuntimeMount:
    source: str
    target: str
    mode: Literal["ro", "rw"] = "rw"


@dataclass(slots=True, frozen=True)
class RuntimePort:
    name: str
    host: int | str
    container: int | str
    protocol: Literal["tcp", "udp"] = "tcp"


@dataclass(slots=True, frozen=True)
class Runtime:
    driver: Literal["docker"]
    image: str
    command: tuple[str, ...]
    workdir: str = "/server"
    memory: str | None = None
    stop_signal: str = "SIGINT"
    stop_timeout: int = 30
    restart: str = "no"
    restart_limit: int = 0
    run_as: str | None = None
    read_only_root: bool = True
    mounts: tuple[RuntimeMount, ...] = ()
    ports: tuple[RuntimePort, ...] = ()


@dataclass(slots=True, frozen=True)
class BuildPermissions:
    network: bool = False


@dataclass(slots=True, frozen=True)
class Build:
    driver: Literal["dockerfile"]
    file: str
    output: str
    timeout: int = 1200
    cpu: int = 2
    memory: str = "2g"
    permissions: BuildPermissions = field(default_factory=BuildPermissions)


@dataclass(slots=True, frozen=True)
class Check:
    id: str
    phase: str
    kind: str
    required: bool = True
    path: str | None = None
    pattern: str | None = None
    host: str | None = None
    port: int | str | None = None
    command: tuple[str, ...] = ()
    timeout: int = 30


@dataclass(slots=True, frozen=True)
class UpdatePolicy:
    strategy: Literal["transactional"] = "transactional"
    backup: tuple[str, ...] = ()
    retain_backups: int = 3
    rollback_on_failure: bool = True


@dataclass(slots=True, frozen=True)
class Permissions:
    build: bool = False
    host_commands: Literal[False] = False


@dataclass(slots=True, frozen=True)
class Manifest:
    manifest_version: Literal[1]
    package: Package
    sources: tuple[SourceSpec, ...]
    runtime: Runtime
    inputs: tuple[InputSpec, ...] = ()
    files: tuple[FileSpec, ...] = ()
    build: Build | None = None
    checks: tuple[Check, ...] = ()
    update: UpdatePolicy = field(default_factory=UpdatePolicy)
    permissions: Permissions = field(default_factory=Permissions)
    extensions: dict[str, Any] = field(default_factory=dict)
    digest: str = ""


def _string_array(value: Any, path: str) -> tuple[str, ...]:
    result = []

    for index, item in enumerate(require_array(value, path)):
        result.append(require_string(item, f"{path}[{index}]"))

    return tuple(result)


def _parse_package(value: Any) -> Package:
    path = "package"
    table = require_table(value, path)
    reject_unknown(
        table,
        {
            "name",
            "version",
            "description",
            "license",
            "authors",
            "platforms",
            "repository",
        },
        path,
    )
    require_keys(table, {"name", "version"}, path)
    name = require_string(table["name"], f"{path}.name")
    version = require_string(table["version"], f"{path}.version")

    if not PACKAGE_NAME_RE.fullmatch(name):
        fail(f"{path}.name", "must be a lowercase package identifier")

    if not SEMVER_RE.fullmatch(version):
        fail(f"{path}.version", "must be a semantic version")

    platforms = _string_array(table.get("platforms", []), f"{path}.platforms")

    for index, platform in enumerate(platforms):
        if not PLATFORM_RE.fullmatch(platform):
            fail(f"{path}.platforms[{index}]", "expected os/architecture")

    repository = None

    if "repository" in table:
        repository_table = require_table(table["repository"], f"{path}.repository")
        reject_unknown(repository_table, {"url"}, f"{path}.repository")
        require_keys(repository_table, {"url"}, f"{path}.repository")
        repository = Repository(
            validate_https_url(repository_table["url"], f"{path}.repository.url")
        )

    return Package(
        name=name,
        version=version,
        description=require_string(
            table.get("description", ""), f"{path}.description", non_empty=False
        ),
        license=optional_string(table, "license", path),
        authors=_string_array(table.get("authors", []), f"{path}.authors"),
        platforms=platforms,
        repository=repository,
    )


def _parse_inputs(value: Any) -> tuple[InputSpec, ...]:
    table = require_table(value, "inputs")
    result = []

    for name, raw_input in table.items():
        path = f"inputs.{name}"
        spec = require_table(raw_input, path)
        reject_unknown(
            spec,
            {"type", "default", "prompt", "min", "max", "pattern", "required", "secret"},
            path,
        )
        require_keys(spec, {"type"}, path)
        input_type = require_string(spec["type"], f"{path}.type")

        if input_type not in {"string", "integer", "boolean"}:
            fail(f"{path}.type", "must be string, integer, or boolean")

        default = spec.get("default")

        if default is not None:
            expected = {"string": str, "integer": int, "boolean": bool}[input_type]

            if not isinstance(default, expected) or (
                input_type == "integer" and isinstance(default, bool)
            ):
                fail(f"{path}.default", f"expected {input_type}")

        minimum = None
        maximum = None

        if "min" in spec:
            minimum = require_int(spec["min"], f"{path}.min")

        if "max" in spec:
            maximum = require_int(spec["max"], f"{path}.max")

        if minimum is not None and maximum is not None and minimum > maximum:
            fail(path, "min may not exceed max")

        pattern = optional_string(spec, "pattern", path)

        if pattern is not None:
            try:
                re.compile(pattern)
            except re.error as exc:
                fail(f"{path}.pattern", f"invalid regular expression: {exc}")

        if isinstance(default, int) and not isinstance(default, bool):
            if minimum is not None and default < minimum:
                fail(f"{path}.default", "is below min")

            if maximum is not None and default > maximum:
                fail(f"{path}.default", "is above max")

        result.append(
            InputSpec(
                name=name,
                type=input_type,  # type: ignore[arg-type]
                default=cast(str | int | bool | None, default),
                prompt=optional_string(spec, "prompt", path),
                minimum=minimum,
                maximum=maximum,
                pattern=pattern,
                required=require_bool(spec.get("required", False), f"{path}.required"),
                secret=require_bool(spec.get("secret", False), f"{path}.secret"),
            )
        )

    return tuple(result)


def _parse_sources(value: Any) -> tuple[SourceSpec, ...]:
    result = []
    seen = set()
    allowed = {
        "id",
        "provider",
        "target",
        "repository",
        "url",
        "version",
        "channel",
        "asset",
        "group",
        "artifact",
        "packaging",
        "classifier",
        "job",
        "build",
        "path",
        "max_size",
        "update",
        "integrity",
        "extract",
        "allow_http",
        "allow_private_network",
        "platforms",
    }

    for index, raw_source in enumerate(require_array(value, "sources")):
        path = f"sources[{index}]"
        table = require_table(raw_source, path)
        reject_unknown(table, allowed, path)
        require_keys(table, {"id", "provider", "target"}, path)
        source_id = require_string(table["id"], f"{path}.id")
        provider = require_string(table["provider"], f"{path}.provider")

        if source_id in seen:
            fail(f"{path}.id", "source ids must be unique")

        seen.add(source_id)

        if provider not in SOURCE_PROVIDERS:
            fail(f"{path}.provider", f"unsupported provider: {provider}")

        allow_http = require_bool(
            table.get("allow_http", False), f"{path}.allow_http"
        )
        url = optional_string(table, "url", path)

        if url is not None:
            validate_https_url(url, f"{path}.url", allow_http=allow_http)

        build_value = table.get("build")

        if build_value is not None and (
            isinstance(build_value, bool) or not isinstance(build_value, (str, int))
        ):
            fail(f"{path}.build", "expected a string or integer")

        source = SourceSpec(
            id=source_id,
            provider=provider,
            target=safe_relative_path(table["target"], f"{path}.target"),
            repository=optional_string(table, "repository", path),
            url=url,
            version=optional_string(table, "version", path),
            channel=require_string(table.get("channel", "stable"), f"{path}.channel"),
            asset=optional_string(table, "asset", path),
            group=optional_string(table, "group", path),
            artifact=optional_string(table, "artifact", path),
            packaging=optional_string(table, "packaging", path),
            classifier=optional_string(table, "classifier", path),
            job=optional_string(table, "job", path),
            build=build_value,
            path=(
                safe_relative_path(table["path"], f"{path}.path")
                if "path" in table
                else None
            ),
            max_size=require_int(
                table.get("max_size", 536_870_912),
                f"{path}.max_size",
                minimum=1,
            ),
            update=require_string(table.get("update", "pinned"), f"{path}.update"),
            integrity=require_string(
                table.get("integrity", "sha256-required"), f"{path}.integrity"
            ),
            extract=require_bool(table.get("extract", False), f"{path}.extract"),
            allow_http=allow_http,
            allow_private_network=require_bool(
                table.get("allow_private_network", False),
                f"{path}.allow_private_network",
            ),
            platforms=_string_array(
                table.get("platforms", []), f"{path}.platforms"
            ),
        )
        for platform_index, platform_name in enumerate(source.platforms):
            if not PLATFORM_RE.fullmatch(platform_name):
                fail(
                    f"{path}.platforms[{platform_index}]",
                    "expected os/architecture",
                )

        _validate_provider_fields(source, path)
        result.append(source)

    if not result:
        fail("sources", "at least one source is required")

    return tuple(result)


def _validate_provider_fields(source: SourceSpec, path: str) -> None:
    if source.provider == "github-release" and not (
        source.repository and source.asset
    ):
        fail(path, "github-release requires repository and asset")

    if source.provider == "maven" and not (
        source.repository and source.group and source.artifact and source.version
    ):
        fail(path, "maven requires repository, group, artifact, and version")

    if source.provider == "jenkins" and not (
        source.url and source.job and source.asset
    ):
        fail(path, "jenkins requires url, job, and asset")

    if source.provider == "http" and source.url is None:
        fail(path, "http requires url")

    if source.provider == "local-file" and source.path is None:
        fail(path, "local-file requires path")


def _parse_files(value: Any) -> tuple[FileSpec, ...]:
    result = []
    targets = set()

    for index, raw_file in enumerate(require_array(value, "files")):
        path = f"files[{index}]"
        table = require_table(raw_file, path)
        reject_unknown(table, {"source", "target", "mode", "template", "executable"}, path)
        require_keys(table, {"source", "target"}, path)
        target = safe_relative_path(table["target"], f"{path}.target")
        mode = require_string(table.get("mode", "managed"), f"{path}.mode")

        if target in targets:
            fail(f"{path}.target", "file targets must be unique")

        targets.add(target)

        if mode not in FILE_MODES:
            fail(f"{path}.mode", "unsupported ownership mode")

        result.append(
            FileSpec(
                source=safe_relative_path(table["source"], f"{path}.source"),
                target=target,
                mode=mode,  # type: ignore[arg-type]
                template=require_bool(table.get("template", False), f"{path}.template"),
                executable=require_bool(
                    table.get("executable", False), f"{path}.executable"
                ),
            )
        )

    return tuple(result)


def _parse_runtime(value: Any) -> Runtime:
    path = "runtime"
    table = require_table(value, path)
    reject_unknown(
        table,
        {
            "driver",
            "image",
            "command",
            "workdir",
            "memory",
            "stop_signal",
            "stop_timeout",
            "restart",
            "restart_limit",
            "run_as",
            "read_only_root",
            "mounts",
            "ports",
        },
        path,
    )
    require_keys(table, {"driver", "image", "command"}, path)
    driver = require_string(table["driver"], f"{path}.driver")

    if driver != "docker":
        fail(f"{path}.driver", "only docker is supported in schema v1")

    raw_command = require_array(table["command"], f"{path}.command")
    command = tuple(
        require_string(item, f"{path}.command[{index}]")
        for index, item in enumerate(raw_command)
    )

    if not command:
        fail(f"{path}.command", "must contain at least one argv element")

    mounts = []

    for index, raw_mount in enumerate(require_array(table.get("mounts", []), f"{path}.mounts")):
        item_path = f"{path}.mounts[{index}]"
        mount = require_table(raw_mount, item_path)
        reject_unknown(mount, {"source", "target", "mode"}, item_path)
        require_keys(mount, {"source", "target"}, item_path)
        mode = require_string(mount.get("mode", "rw"), f"{item_path}.mode")

        if mode not in {"ro", "rw"}:
            fail(f"{item_path}.mode", "must be ro or rw")

        mounts.append(
            RuntimeMount(
                source=safe_relative_path(
                    mount["source"], f"{item_path}.source", allow_dot=True
                ),
                target=require_string(mount["target"], f"{item_path}.target"),
                mode=mode,  # type: ignore[arg-type]
            )
        )

    ports = []

    for index, raw_port in enumerate(require_array(table.get("ports", []), f"{path}.ports")):
        item_path = f"{path}.ports[{index}]"
        port = require_table(raw_port, item_path)
        reject_unknown(port, {"name", "host", "container", "protocol"}, item_path)
        require_keys(port, {"name", "host", "container"}, item_path)
        protocol = require_string(port.get("protocol", "tcp"), f"{item_path}.protocol")

        if protocol not in {"tcp", "udp"}:
            fail(f"{item_path}.protocol", "must be tcp or udp")

        host = _parse_port_value(port["host"], f"{item_path}.host")
        container = _parse_port_value(port["container"], f"{item_path}.container")
        ports.append(
            RuntimePort(
                name=require_string(port["name"], f"{item_path}.name"),
                host=host,
                container=container,
                protocol=protocol,  # type: ignore[arg-type]
            )
        )

    return Runtime(
        driver="docker",
        image=require_string(table["image"], f"{path}.image"),
        command=command,
        workdir=require_string(table.get("workdir", "/server"), f"{path}.workdir"),
        memory=optional_string(table, "memory", path),
        stop_signal=require_string(table.get("stop_signal", "SIGINT"), f"{path}.stop_signal"),
        stop_timeout=require_int(
            table.get("stop_timeout", 30), f"{path}.stop_timeout", minimum=1
        ),
        restart=require_string(table.get("restart", "no"), f"{path}.restart"),
        restart_limit=require_int(
            table.get("restart_limit", 0), f"{path}.restart_limit", minimum=0
        ),
        run_as=optional_string(table, "run_as", path),
        read_only_root=require_bool(
            table.get("read_only_root", True), f"{path}.read_only_root"
        ),
        mounts=tuple(mounts),
        ports=tuple(ports),
    )


def _parse_port_value(value: Any, path: str) -> int | str:
    if isinstance(value, int) and not isinstance(value, bool):
        return require_int(value, path, minimum=1, maximum=65535)

    text = require_string(value, path)

    if not text.startswith("${input.") or not text.endswith("}"):
        fail(path, "must be a port number or ${input.name}")

    return text


def _parse_build(value: Any) -> Build:
    path = "build"
    table = require_table(value, path)
    reject_unknown(table, {"driver", "file", "output", "timeout", "cpu", "memory", "permissions"}, path)
    require_keys(table, {"driver", "file", "output"}, path)
    driver = require_string(table["driver"], f"{path}.driver")

    if driver != "dockerfile":
        fail(f"{path}.driver", "only dockerfile is supported in schema v1")

    permissions = BuildPermissions()

    if "permissions" in table:
        permission_table = require_table(table["permissions"], f"{path}.permissions")
        reject_unknown(permission_table, {"network"}, f"{path}.permissions")
        permissions = BuildPermissions(
            network=require_bool(
                permission_table.get("network", False),
                f"{path}.permissions.network",
            )
        )

    output = require_string(table["output"], f"{path}.output")

    if not output.startswith("/"):
        fail(f"{path}.output", "must be an absolute container path")

    return Build(
        driver="dockerfile",
        file=safe_relative_path(table["file"], f"{path}.file"),
        output=output,
        timeout=require_int(table.get("timeout", 1200), f"{path}.timeout", minimum=1),
        cpu=require_int(table.get("cpu", 2), f"{path}.cpu", minimum=1),
        memory=require_string(table.get("memory", "2g"), f"{path}.memory"),
        permissions=permissions,
    )


def _parse_checks(value: Any) -> tuple[Check, ...]:
    result = []
    seen = set()

    for index, raw_check in enumerate(require_array(value, "checks")):
        path = f"checks[{index}]"
        table = require_table(raw_check, path)
        reject_unknown(
            table,
            {
                "id",
                "phase",
                "kind",
                "required",
                "path",
                "pattern",
                "host",
                "port",
                "command",
                "timeout",
            },
            path,
        )
        require_keys(table, {"id", "phase", "kind"}, path)
        check_id = require_string(table["id"], f"{path}.id")
        phase = require_string(table["phase"], f"{path}.phase")
        kind = require_string(table["kind"], f"{path}.kind")

        if check_id in seen:
            fail(f"{path}.id", "check ids must be unique")

        seen.add(check_id)

        if phase not in CHECK_PHASES:
            fail(f"{path}.phase", "unsupported check phase")

        if kind not in CHECK_KINDS:
            fail(f"{path}.kind", "unsupported check kind")

        check_path = (
            safe_relative_path(table["path"], f"{path}.path")
            if "path" in table
            else None
        )
        pattern = optional_string(table, "pattern", path)

        if kind == "file" and check_path is None:
            fail(path, "file checks require path")

        if kind == "log-regex" and pattern is None:
            fail(path, "log-regex checks require pattern")

        command = tuple(
            require_string(item, f"{path}.command[{command_index}]")
            for command_index, item in enumerate(
                require_array(table.get("command", []), f"{path}.command")
            )
        )

        if kind == "command" and not command:
            fail(path, "command checks require a non-empty argv array")

        if phase in {"post-build", "post-install"} and kind != "file":
            fail(path, f"{phase} currently supports only file checks")

        if phase == "readiness" and kind == "file":
            fail(path, "readiness file checks must use post-install phase")

        port = table.get("port")

        if port is not None:
            port = _parse_port_value(port, f"{path}.port")

        result.append(
            Check(
                id=check_id,
                phase=phase,
                kind=kind,
                required=require_bool(table.get("required", True), f"{path}.required"),
                path=check_path,
                pattern=pattern,
                host=optional_string(table, "host", path),
                port=port,
                command=command,
                timeout=require_int(table.get("timeout", 30), f"{path}.timeout", minimum=1),
            )
        )

    return tuple(result)


def _parse_update(value: Any) -> UpdatePolicy:
    path = "update"
    table = require_table(value, path)
    reject_unknown(table, {"strategy", "backup", "retain_backups", "rollback_on_failure"}, path)
    strategy = require_string(table.get("strategy", "transactional"), f"{path}.strategy")

    if strategy != "transactional":
        fail(f"{path}.strategy", "only transactional updates are supported")

    return UpdatePolicy(
        backup=tuple(
            safe_relative_path(item, f"{path}.backup[{index}]")
            for index, item in enumerate(require_array(table.get("backup", []), f"{path}.backup"))
        ),
        retain_backups=require_int(
            table.get("retain_backups", 3),
            f"{path}.retain_backups",
            minimum=0,
        ),
        rollback_on_failure=require_bool(
            table.get("rollback_on_failure", True),
            f"{path}.rollback_on_failure",
        ),
    )


def _parse_permissions(value: Any) -> Permissions:
    path = "permissions"
    table = require_table(value, path)
    reject_unknown(table, {"build", "host_commands"}, path)
    host_commands = require_bool(
        table.get("host_commands", False), f"{path}.host_commands"
    )

    if host_commands:
        fail(f"{path}.host_commands", "host commands are forbidden")

    return Permissions(
        build=require_bool(table.get("build", False), f"{path}.build"),
        host_commands=False,
    )


def parse_manifest(content: bytes, *, source: str = MANIFEST_NAME) -> Manifest:
    if len(content) > MAX_MANIFEST_SIZE:
        raise ValidationError(
            f"{source} exceeds the {MAX_MANIFEST_SIZE}-byte limit",
            path=source,
            size=len(content),
        )

    try:
        text = content.decode("utf-8")
        raw = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValidationError(f"invalid {source}: {exc}", path=source) from exc

    reject_unknown(
        raw,
        {
            "manifest_version",
            "package",
            "inputs",
            "sources",
            "files",
            "runtime",
            "build",
            "checks",
            "update",
            "permissions",
            "x",
        },
        "manifest",
    )
    require_keys(raw, {"manifest_version", "package", "sources", "runtime"}, "manifest")
    manifest_version = require_int(raw["manifest_version"], "manifest_version")

    if manifest_version != 1:
        fail("manifest_version", "unsupported schema version; expected 1")

    extensions = require_table(raw.get("x", {}), "x")

    for vendor, extension in extensions.items():
        require_table(extension, f"x.{vendor}")

    build = _parse_build(raw["build"]) if "build" in raw else None
    permissions = _parse_permissions(raw.get("permissions", {}))

    if build is not None and not permissions.build:
        fail("permissions.build", "must be true when a Dockerfile build is declared")

    return Manifest(
        manifest_version=1,
        package=_parse_package(raw["package"]),
        inputs=_parse_inputs(raw.get("inputs", {})),
        sources=_parse_sources(raw["sources"]),
        files=_parse_files(raw.get("files", [])),
        runtime=_parse_runtime(raw["runtime"]),
        build=build,
        checks=_parse_checks(raw.get("checks", [])),
        update=_parse_update(raw.get("update", {})),
        permissions=permissions,
        extensions=extensions,
        digest=sha256_digest(content),
    )


def load_manifest(path: Path) -> Manifest:
    if path.name != MANIFEST_NAME:
        raise ValidationError(
            f"manifest must be named exactly {MANIFEST_NAME}", path=str(path)
        )

    return parse_manifest(read_bounded_utf8(path, MAX_MANIFEST_SIZE), source=str(path))
