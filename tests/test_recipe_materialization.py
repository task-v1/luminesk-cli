from __future__ import annotations

from pathlib import Path

from luminesk_cli.infrastructure.recipe import (
    cleanup_materialized,
    materialize_local_recipe,
)


def test_failed_install_cleanup_preserves_concurrently_changed_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "recipe"
    source.mkdir()
    (source / "luminesk.toml").write_text("original", encoding="utf-8")
    (source / "unchanged.txt").write_text("unchanged", encoding="utf-8")
    target = tmp_path / "target"
    copied = materialize_local_recipe(source, target)
    (target / "luminesk.toml").write_text("user edit", encoding="utf-8")

    cleanup_materialized(target, copied)

    assert (target / "luminesk.toml").read_text(encoding="utf-8") == "user edit"
    assert not (target / "unchanged.txt").exists()
    assert target.exists()
