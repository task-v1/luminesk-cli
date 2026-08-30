from __future__ import annotations

from luminesk_cli.bundled_recipes import BUNDLED_RECIPE_IDS, recipe_root
from luminesk_cli.domain.manifest import load_manifest


def test_all_bundled_recipes_are_strict_nesk_2_manifests() -> None:
    assert len(BUNDLED_RECIPE_IDS) == 12

    for recipe_id in BUNDLED_RECIPE_IDS:
        root = recipe_root(recipe_id)
        manifest = load_manifest(root / "luminesk.toml")

        assert manifest.manifest_version == 1
        assert manifest.runtime.command
        assert manifest.sources


def test_pumpkin_uses_platform_specific_artifacts() -> None:
    manifest = load_manifest(recipe_root("pumpkin") / "luminesk.toml")
    sources = {source.id: source for source in manifest.sources}

    assert sources["core-amd64"].platforms == ("linux/amd64",)
    assert sources["core-arm64"].platforms == ("linux/arm64",)
    assert all(source.target == "pumpkin" for source in sources.values())


def test_complex_recipes_declare_isolated_dockerfile_builds() -> None:
    for recipe_id in ("dragonfly", "endstone"):
        root = recipe_root(recipe_id)
        manifest = load_manifest(root / "luminesk.toml")

        assert manifest.build is not None
        assert manifest.build.network is True
        assert (root / manifest.build.file).is_file()
