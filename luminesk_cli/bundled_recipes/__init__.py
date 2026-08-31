"""Data-only Luminesk 2.0 recipes shipped as catalog fixtures."""

from __future__ import annotations

from pathlib import Path

from luminesk_cli.domain.errors import ValidationError

BUNDLED_RECIPE_IDS = (
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


def recipe_root(recipe_id: str) -> Path:
    if recipe_id not in BUNDLED_RECIPE_IDS:
        raise ValidationError(f"no bundled recipe named {recipe_id}")

    return Path(__file__).parent / recipe_id
