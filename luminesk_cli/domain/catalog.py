"""Strict models for the small Git-backed recipe catalog."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.primitives import (
    PACKAGE_NAME_RE,
    reject_unknown,
    require_array,
    require_int,
    require_keys,
    require_string,
    require_table,
    safe_relative_path,
    validate_https_url,
)

CATALOG_VERSION = 1
MAX_CATALOG_ENTRY_SIZE = 256 * 1024
MAX_CATALOG_ENTRIES = 10_000
TRUST_LEVELS = frozenset({"official", "verified", "community", "direct"})


@dataclass(slots=True, frozen=True)
class CatalogEntry:
    name: str
    namespace: str
    repository: str
    manifest: str
    maintainers: tuple[str, ...]
    license: str
    trust: Literal["official", "verified", "community", "direct"]
    description: str = ""
    type: Literal["core", "template"] = "core"
    deprecated: bool = False
    replaced_by: str | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}/{self.name}"


def parse_catalog_entry(content: bytes, *, source: str = "catalog entry") -> CatalogEntry:
    if len(content) > MAX_CATALOG_ENTRY_SIZE:
        raise ValidationError(f"{source} exceeds the catalog entry size limit")

    try:
        raw = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValidationError(f"invalid {source}: {exc}") from exc

    table = require_table(raw, "catalog")
    allowed = {
        "catalog_version",
        "name",
        "namespace",
        "repository",
        "manifest",
        "maintainers",
        "license",
        "trust",
        "description",
        "type",
        "deprecated",
        "replaced_by",
    }
    reject_unknown(table, allowed, "catalog")
    require_keys(
        table,
        {
            "catalog_version",
            "name",
            "namespace",
            "repository",
            "manifest",
            "maintainers",
            "license",
            "trust",
        },
        "catalog",
    )
    version = require_int(table["catalog_version"], "catalog.catalog_version")

    if version != CATALOG_VERSION:
        raise ValidationError(f"unsupported catalog version {version}")

    name = _identifier(table["name"], "catalog.name")
    namespace = _identifier(table["namespace"], "catalog.namespace")
    maintainers = tuple(
        require_string(value, f"catalog.maintainers[{index}]")
        for index, value in enumerate(
            require_array(table["maintainers"], "catalog.maintainers")
        )
    )

    if not maintainers:
        raise ValidationError("catalog.maintainers may not be empty")

    trust = require_string(table["trust"], "catalog.trust")

    if trust not in TRUST_LEVELS:
        raise ValidationError("catalog.trust has an unsupported value")

    entry_type = require_string(table.get("type", "core"), "catalog.type")

    if entry_type not in {"core", "template"}:
        raise ValidationError("catalog.type must be core or template")

    deprecated = table.get("deprecated", False)

    if not isinstance(deprecated, bool):
        raise ValidationError("catalog.deprecated must be a boolean")

    replaced_by = table.get("replaced_by")

    if replaced_by is not None:
        replaced_by = require_string(replaced_by, "catalog.replaced_by")

    return CatalogEntry(
        name=name,
        namespace=namespace,
        repository=validate_https_url(table["repository"], "catalog.repository"),
        manifest=safe_relative_path(table["manifest"], "catalog.manifest"),
        maintainers=maintainers,
        license=require_string(table["license"], "catalog.license"),
        trust=trust,  # type: ignore[arg-type]
        description=require_string(
            table.get("description", ""),
            "catalog.description",
            non_empty=False,
        ),
        type=entry_type,  # type: ignore[arg-type]
        deprecated=deprecated,
        replaced_by=replaced_by,
    )


def load_catalog(directory: Path) -> tuple[CatalogEntry, ...]:
    if not directory.is_dir():
        raise ValidationError(f"catalog directory does not exist: {directory}")

    paths = sorted(directory.glob("*.toml"))

    if len(paths) > MAX_CATALOG_ENTRIES:
        raise ValidationError("catalog contains too many entries")

    entries = []
    qualified_names = set()

    for path in paths:
        entry = parse_catalog_entry(path.read_bytes(), source=str(path))

        if entry.qualified_name in qualified_names:
            raise ValidationError(
                f"duplicate catalog entry: {entry.qualified_name}"
            )

        qualified_names.add(entry.qualified_name)
        entries.append(entry)

    return tuple(entries)


def _identifier(value: Any, path: str) -> str:
    identifier = require_string(value, path)

    if not PACKAGE_NAME_RE.fullmatch(identifier):
        raise ValidationError(f"{path} must be a lowercase identifier")

    return identifier
