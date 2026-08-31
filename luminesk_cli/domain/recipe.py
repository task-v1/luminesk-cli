"""Unified recipe origin and canonical snapshot models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from luminesk_cli.domain.manifest import Manifest


@dataclass(slots=True, frozen=True)
class RecipeOrigin:
    kind: Literal["database", "github", "local"]
    source: str
    revision: str
    tracking: bool
    version: str
    manifest_digest: str
    template_digest: str | None = None
    ref: str | None = None
    entry: str | None = None
    path: str | None = None


@dataclass(slots=True, frozen=True)
class RecipeSnapshotEntry:
    path: str
    type: Literal["file", "directory"]
    mode: int
    size: int
    digest: str | None


@dataclass(slots=True, frozen=True)
class RecipeSnapshot:
    root: Path
    manifest: Manifest
    origin: RecipeOrigin
    entries: tuple[RecipeSnapshotEntry, ...]
