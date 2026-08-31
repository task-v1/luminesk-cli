from __future__ import annotations

from pathlib import Path

from luminesk_cli.domain.manifest import load_manifest
from luminesk_cli.infrastructure.template import read_template_tree

FIXTURES = Path(__file__).parent / "fixtures" / "recipes"


def test_java_reference_recipes_cover_vanilla_and_paper() -> None:
    expected_sources = {
        "vanilla-java": "mojang-version",
        "paper-java": "paper",
    }
    for name, source_type in expected_sources.items():
        root = FIXTURES / name
        manifest = load_manifest(root / "luminesk.toml")
        inputs = {item.name: item for item in manifest.inputs}

        assert manifest.package.edition == "java"
        assert manifest.sources[0].type == source_type
        assert manifest.runtime.image == "eclipse-temurin:21-jre"
        assert manifest.runtime.memory == "${input.memory}"
        assert manifest.runtime.ports[0].host == 25565
        assert manifest.runtime.ports[0].protocol == "tcp"
        assert inputs["eula"].required is True
        assert inputs["eula"].type == "boolean"
        assert any("${input.memory}" in value for value in manifest.runtime.command)
        assert manifest.ownership.preserve == ("server.properties",)
        assert "world" in manifest.ownership.data

        tree = read_template_tree(root, manifest)
        assert tree is not None
        assert {entry.target for entry in tree.entries if entry.type == "file"} == {
            "eula.txt",
            "server.properties",
        }


def test_bedrock_reference_recipes_cover_maven_and_php() -> None:
    lumi = load_manifest(FIXTURES / "lumi-bedrock" / "luminesk.toml")
    pocketmine = load_manifest(FIXTURES / "pocketmine-bedrock" / "luminesk.toml")

    assert lumi.package.edition == "bedrock"
    assert lumi.sources[0].type == "maven"
    assert lumi.runtime.ports[0].host == 19132
    assert lumi.runtime.ports[0].protocol == "udp"
    assert pocketmine.package.edition == "bedrock"
    assert pocketmine.sources[0].type == "http"
    assert pocketmine.runtime.command[0] == "php"
    assert pocketmine.runtime.ports[0].host == 19132
    assert pocketmine.runtime.ports[0].protocol == "udp"


def test_reference_recipes_are_test_only() -> None:
    assert "tests/fixtures" in FIXTURES.as_posix()
