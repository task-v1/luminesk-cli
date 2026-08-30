from __future__ import annotations

from pathlib import Path

from luminesk_cli.domain.manifest import parse_manifest
from luminesk_cli.infrastructure.recipe_snapshot import (
    create_recipe_snapshot,
    stage_recipe_snapshot,
)


def test_snapshot_contains_only_declared_recipe_assets(tmp_path: Path) -> None:
    root = tmp_path / "upstream"
    (root / ".nesk/template").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    manifest_bytes = b"""\
manifest_version = 1
template = ".nesk/template"
[package]
name = "upstream-fixture"
version = "1.4.0"
kind = "core"
game = "minecraft"
edition = "java"
[runtime]
image = "example/server:2"
command = ["./server"]
"""
    (root / "luminesk.toml").write_bytes(manifest_bytes)
    (root / ".nesk/template/server.toml.tmpl").write_text(
        "name=${input.name}\n",
        encoding="utf-8",
    )
    (root / "src/main.cpp").write_text("source", encoding="utf-8")
    (root / "tests/test.cpp").write_text("tests", encoding="utf-8")
    (root / "README.md").write_text("docs", encoding="utf-8")
    snapshot = create_recipe_snapshot(
        root,
        parse_manifest(manifest_bytes),
        kind="github",
        source="github:owner/upstream",
        revision="a" * 40,
        ref="main",
        tracking=True,
    )
    staged = tmp_path / "staged"

    stage_recipe_snapshot(snapshot, staged)

    assert (staged / "luminesk.toml").is_file()
    assert (staged / ".nesk/template/server.toml.tmpl").is_file()
    assert not (staged / "src").exists()
    assert not (staged / "tests").exists()
    assert not (staged / "README.md").exists()
    assert snapshot.origin.kind == "github"
    assert snapshot.origin.revision == "a" * 40
    assert snapshot.origin.template_digest is not None
