from __future__ import annotations

import json
from pathlib import Path

import pytest

from luminesk_cli.cli.entry import main
from luminesk_cli.domain.catalog import load_catalog, parse_catalog_entry
from luminesk_cli.domain.errors import ValidationError

ENTRY = b"""\
catalog_version = 1
name = "fixture"
namespace = "community"
repository = "https://github.com/example/fixture"
manifest = "luminesk.toml"
maintainers = ["github:example"]
license = "MIT"
trust = "community"
description = "Fixture recipe"
"""


def test_catalog_is_strict_and_rejects_duplicate_names(tmp_path: Path) -> None:
    (tmp_path / "one.toml").write_bytes(ENTRY)
    (tmp_path / "two.toml").write_bytes(ENTRY)

    with pytest.raises(ValidationError, match="duplicate"):
        load_catalog(tmp_path)

    with pytest.raises(ValidationError, match="unknown key"):
        parse_catalog_entry(ENTRY + b"unexpected = true\n")


def test_search_and_info_emit_stable_json(tmp_path: Path, capsys) -> None:
    (tmp_path / "fixture.toml").write_bytes(ENTRY)

    assert main(["search", "fixture", "--catalog", str(tmp_path), "--json"]) == 0
    search = json.loads(capsys.readouterr().out)
    assert search["recipes"][0]["qualifiedName"] == "community/fixture"

    assert main(["info", "fixture", "--catalog", str(tmp_path), "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["recipe"]["trust"] == "community"
