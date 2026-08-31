"""Immutable mutation plans produced before install or update writes state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True, frozen=True)
class PlanChange:
    action: Literal["create", "replace", "preserve", "remove", "conflict"]
    path: str
    reason: str
    digest: str | None = None


@dataclass(slots=True, frozen=True)
class Plan:
    operation: Literal["install", "update"]
    target: str
    changes: tuple[PlanChange, ...]
    downloads: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    requires_downtime: bool = False

    @property
    def has_conflicts(self) -> bool:
        return any(change.action == "conflict" for change in self.changes)
