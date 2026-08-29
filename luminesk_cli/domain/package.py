"""Immutable installable package metadata used as the transaction boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.primitives import (
    reject_unknown,
    require_int,
    require_keys,
    require_string,
    require_table,
    safe_relative_path,
    validate_digest,
)

PACKAGE_FORMAT_VERSION = 1
PACKAGE_SUFFIX = ".neskpkg"


@dataclass(slots=True, frozen=True)
class PackageFile:
    path: str
    type: Literal["file", "directory"]
    mode: int
    size: int
    digest: str | None
    ownership: Literal["managed", "preserve", "generated", "data"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "type": self.type,
            "mode": self.mode,
            "size": self.size,
            "digest": self.digest,
            "ownership": self.ownership,
        }


@dataclass(slots=True, frozen=True)
class PackageMetadata:
    name: str
    version: str
    manifest_digest: str
    lock_digest: str
    target: str
    files: tuple[PackageFile, ...]
    recipe_revision: str | None = None
    format_version: int = PACKAGE_FORMAT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "formatVersion": self.format_version,
            "name": self.name,
            "version": self.version,
            "manifestDigest": self.manifest_digest,
            "lockDigest": self.lock_digest,
            "target": self.target,
            "recipeRevision": self.recipe_revision,
            "files": [item.to_dict() for item in self.files],
        }

    def to_bytes(self) -> bytes:
        return (
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


@dataclass(slots=True, frozen=True)
class ServerPackage:
    path: Path
    digest: str
    size: int
    metadata: PackageMetadata


def parse_package_metadata(content: bytes) -> PackageMetadata:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("package metadata is not valid UTF-8 JSON") from exc

    table = require_table(value, "package")
    reject_unknown(
        table,
        {
            "formatVersion",
            "name",
            "version",
            "manifestDigest",
            "lockDigest",
            "target",
            "recipeRevision",
            "files",
        },
        "package",
    )
    require_keys(
        table,
        {
            "formatVersion",
            "name",
            "version",
            "manifestDigest",
            "lockDigest",
            "target",
            "files",
        },
        "package",
    )
    version = require_int(table["formatVersion"], "package.formatVersion")

    if version != PACKAGE_FORMAT_VERSION:
        raise ValidationError(f"unsupported package format version {version}")

    raw_files = table["files"]

    if not isinstance(raw_files, list):
        raise ValidationError("package.files must be an array")

    files = []
    seen = set()

    for index, raw_file in enumerate(raw_files):
        path = f"package.files[{index}]"
        item = require_table(raw_file, path)
        reject_unknown(
            item, {"path", "type", "mode", "size", "digest", "ownership"}, path
        )
        require_keys(
            item, {"path", "type", "mode", "size", "digest", "ownership"}, path
        )
        item_path = safe_relative_path(item["path"], f"{path}.path")
        item_type = require_string(item["type"], f"{path}.type")
        ownership = require_string(item["ownership"], f"{path}.ownership")

        if item_path in seen:
            raise ValidationError(f"duplicate package path: {item_path}")

        seen.add(item_path)

        if item_type not in {"file", "directory"}:
            raise ValidationError(f"{path}.type must be file or directory")

        if ownership not in {"managed", "preserve", "generated", "data"}:
            raise ValidationError(f"{path}.ownership is invalid")

        digest_value = item["digest"]
        digest = None

        if item_type == "file":
            digest = validate_digest(digest_value, f"{path}.digest")
        elif digest_value is not None:
            raise ValidationError(f"{path}.digest must be null for a directory")

        files.append(
            PackageFile(
                path=item_path,
                type=item_type,  # type: ignore[arg-type]
                mode=require_int(
                    item["mode"], f"{path}.mode", minimum=0, maximum=0o777
                ),
                size=require_int(item["size"], f"{path}.size", minimum=0),
                digest=digest,
                ownership=ownership,  # type: ignore[arg-type]
            )
        )

    recipe_revision = table.get("recipeRevision")

    if recipe_revision is not None:
        recipe_revision = require_string(recipe_revision, "package.recipeRevision")

    return PackageMetadata(
        name=require_string(table["name"], "package.name"),
        version=require_string(table["version"], "package.version"),
        manifest_digest=validate_digest(
            table["manifestDigest"], "package.manifestDigest"
        ),
        lock_digest=validate_digest(table["lockDigest"], "package.lockDigest"),
        target=require_string(table["target"], "package.target"),
        recipe_revision=recipe_revision,
        files=tuple(files),
    )
