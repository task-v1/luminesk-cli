from __future__ import annotations

from luminesk_cli.compatibility_recipes import (
    COMPATIBILITY_CORE_IDS,
    recipe_root,
)
from luminesk_cli.domain.manifest import load_manifest


def test_all_twelve_legacy_cores_have_strict_data_recipes() -> None:
    assert len(COMPATIBILITY_CORE_IDS) == 12

    for core_id in COMPATIBILITY_CORE_IDS:
        root = recipe_root(core_id)
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


def test_complex_cores_declare_isolated_dockerfile_builds() -> None:
    for core_id in ("dragonfly", "endstone"):
        root = recipe_root(core_id)
        manifest = load_manifest(root / "luminesk.toml")

        assert manifest.build is not None
        assert manifest.build.driver == "dockerfile"
        assert manifest.permissions.build is True
        assert manifest.permissions.host_commands is False
        assert (root / manifest.build.file).is_file()
