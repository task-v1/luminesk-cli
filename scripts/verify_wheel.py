"""Fail a release if the wheel omits 2.0 data or ships retired 1.x code."""

from __future__ import annotations

import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

REQUIRED_RECIPE_IDS = {
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
}
RETIRED_DIRECTORIES = {"core", "cores", "migration", "models", "utils"}
RETIRED_DEPENDENCIES = {"cyclopts", "rich"}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        raise SystemExit("usage: verify_wheel.py DIST.whl")

    wheel = Path(argv[0])

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]

        if len(metadata_names) != 1:
            raise SystemExit("wheel must contain exactly one METADATA file")

        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        requirements = metadata.get_all("Requires-Dist", [])

    if metadata["Version"] != "2.0.0":
        raise SystemExit(f"unexpected wheel version: {metadata['Version']}")

    normalized_requirements = {
        requirement.split(";", 1)[0].split("[", 1)[0].split(" ", 1)[0].lower()
        for requirement in requirements
    }
    forbidden_dependencies = normalized_requirements & RETIRED_DEPENDENCIES

    if forbidden_dependencies:
        raise SystemExit(
            f"wheel contains retired dependencies: {sorted(forbidden_dependencies)}"
        )

    for directory in RETIRED_DIRECTORIES:
        prefix = f"luminesk_cli/{directory}/"

        if any(name.startswith(prefix) for name in names):
            raise SystemExit(f"wheel contains retired 1.x package: {directory}")

    if any(name.endswith((".pyc", ".pyo")) for name in names):
        raise SystemExit("wheel contains bytecode files")

    missing_recipes = {
        recipe_id
        for recipe_id in REQUIRED_RECIPE_IDS
        if f"luminesk_cli/bundled_recipes/{recipe_id}/luminesk.toml" not in names
    }

    if missing_recipes:
        raise SystemExit(f"wheel omits bundled recipes: {sorted(missing_recipes)}")

    if not any(
        name.startswith("luminesk_cli/community_catalog/recipes/")
        and name.endswith(".toml")
        for name in names
    ):
        raise SystemExit("wheel omits the bundled catalog")

    print(f"Verified {wheel} ({len(names)} members).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
