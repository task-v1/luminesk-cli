"""Data-only migration recipes for the twelve Nesk 1.1 cores."""

from __future__ import annotations

from pathlib import Path

from luminesk_cli.domain.errors import ValidationError

COMPATIBILITY_CORE_IDS = (
    "allay",
    "better-altay",
    "dragonfly",
    "endstone",
    "lumi",
    "lunacy",
    "nukkit",
    "nukkit-mot",
    "pnx",
    "pocketmine",
    "pumpkin",
    "serenity",
)


def recipe_root(core_id: str) -> Path:
    if core_id not in COMPATIBILITY_CORE_IDS:
        raise ValidationError(f"no compatibility recipe for core {core_id}")

    return Path(__file__).parent / core_id
