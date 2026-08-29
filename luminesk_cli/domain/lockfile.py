"""Canonical lockfile v1 models, parser, and crash-safe writer."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.primitives import (
    reject_unknown,
    require_int,
    require_keys,
    require_string,
    require_table,
    safe_relative_path,
    validate_digest,
    validate_https_url,
)

LOCKFILE_NAME = "luminesk.lock"
LOCKFILE_VERSION = 1
MAX_LOCKFILE_SIZE = 4 * 1024 * 1024


@dataclass(slots=True, frozen=True)
class RecipeLock:
    source: str
    revision: str


@dataclass(slots=True, frozen=True)
class ResolvedSource:
    provider: str
    version: str
    source_revision: str
    url: str
    size: int
    digest: str
    target: str
    media_type: str | None = None


@dataclass(slots=True, frozen=True)
class RuntimeLock:
    image: str


@dataclass(slots=True, frozen=True)
class Lockfile:
    manifest_digest: str
    target: str
    sources: dict[str, ResolvedSource]
    runtime: RuntimeLock
    recipe: RecipeLock | None = None
    lockfile_version: int = LOCKFILE_VERSION

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "lockfileVersion": self.lockfile_version,
            "manifestDigest": self.manifest_digest,
            "target": self.target,
            "sources": {
                source_id: {
                    "provider": source.provider,
                    "version": source.version,
                    "sourceRevision": source.source_revision,
                    "url": source.url,
                    "size": source.size,
                    "digest": source.digest,
                    "target": source.target,
                    **(
                        {"mediaType": source.media_type}
                        if source.media_type is not None
                        else {}
                    ),
                }
                for source_id, source in self.sources.items()
            },
            "runtime": {"image": self.runtime.image},
        }

        if self.recipe is not None:
            result["recipe"] = {
                "source": self.recipe.source,
                "revision": self.recipe.revision,
            }

        return result

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

    @property
    def digest(self) -> str:
        from luminesk_cli.domain.primitives import sha256_digest

        return sha256_digest(self.to_bytes())


def _parse_source(source_id: str, value: Any) -> ResolvedSource:
    path = f"sources.{source_id}"
    table = require_table(value, path)
    reject_unknown(
        table,
        {
            "provider",
            "version",
            "sourceRevision",
            "url",
            "size",
            "digest",
            "target",
            "mediaType",
        },
        path,
    )
    require_keys(
        table,
        {"provider", "version", "sourceRevision", "url", "size", "digest", "target"},
        path,
    )
    return ResolvedSource(
        provider=require_string(table["provider"], f"{path}.provider"),
        version=require_string(table["version"], f"{path}.version"),
        source_revision=require_string(
            table["sourceRevision"], f"{path}.sourceRevision"
        ),
        url=validate_https_url(table["url"], f"{path}.url"),
        size=require_int(table["size"], f"{path}.size", minimum=0),
        digest=validate_digest(table["digest"], f"{path}.digest"),
        target=safe_relative_path(table["target"], f"{path}.target"),
        media_type=(
            require_string(table["mediaType"], f"{path}.mediaType")
            if "mediaType" in table
            else None
        ),
    )


def parse_lockfile(content: bytes, *, source: str = LOCKFILE_NAME) -> Lockfile:
    if len(content) > MAX_LOCKFILE_SIZE:
        raise ValidationError(
            f"{source} exceeds the {MAX_LOCKFILE_SIZE}-byte limit",
            path=source,
            size=len(content),
        )

    try:
        raw = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid {source}: {exc}", path=source) from exc

    table = require_table(raw, "lockfile")
    reject_unknown(
        table,
        {"lockfileVersion", "manifestDigest", "recipe", "target", "sources", "runtime"},
        "lockfile",
    )
    require_keys(
        table,
        {"lockfileVersion", "manifestDigest", "target", "sources", "runtime"},
        "lockfile",
    )
    version = require_int(table["lockfileVersion"], "lockfile.lockfileVersion")

    if version != LOCKFILE_VERSION:
        raise ValidationError(
            f"unsupported lockfile version {version}; expected {LOCKFILE_VERSION}"
        )

    sources_table = require_table(table["sources"], "lockfile.sources")
    sources = {
        source_id: _parse_source(source_id, source_value)
        for source_id, source_value in sources_table.items()
    }
    runtime_table = require_table(table["runtime"], "lockfile.runtime")
    reject_unknown(runtime_table, {"image"}, "lockfile.runtime")
    require_keys(runtime_table, {"image"}, "lockfile.runtime")
    image = require_string(runtime_table["image"], "lockfile.runtime.image")

    if "@sha256:" not in image:
        raise ValidationError("lockfile.runtime.image must be pinned by sha256 digest")

    recipe = None

    if "recipe" in table:
        recipe_table = require_table(table["recipe"], "lockfile.recipe")
        reject_unknown(recipe_table, {"source", "revision"}, "lockfile.recipe")
        require_keys(recipe_table, {"source", "revision"}, "lockfile.recipe")
        recipe = RecipeLock(
            source=require_string(recipe_table["source"], "lockfile.recipe.source"),
            revision=require_string(
                recipe_table["revision"], "lockfile.recipe.revision"
            ),
        )

    return Lockfile(
        manifest_digest=validate_digest(
            table["manifestDigest"], "lockfile.manifestDigest"
        ),
        target=require_string(table["target"], "lockfile.target"),
        sources=sources,
        runtime=RuntimeLock(image=image),
        recipe=recipe,
    )


def load_lockfile(path: Path) -> Lockfile:
    if path.name != LOCKFILE_NAME:
        raise ValidationError(
            f"lockfile must be named exactly {LOCKFILE_NAME}", path=str(path)
        )

    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}", path=str(path)) from exc

    return parse_lockfile(content, source=str(path))


def write_lockfile(path: Path, lockfile: Lockfile) -> None:
    if path.name != LOCKFILE_NAME:
        raise ValidationError(
            f"lockfile must be named exactly {LOCKFILE_NAME}", path=str(path)
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(lockfile.to_bytes())
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
