from __future__ import annotations

import json
from pathlib import Path

from luminesk_cli.domain.manifest import SOURCE_TYPES

ROOT = Path(__file__).parents[1]
SCHEMAS = ROOT / "schemas"


def _json(name: str) -> dict[str, object]:
    value = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_supported_source_types_match_runtime_registry() -> None:
    metadata = _json("supported-source-types-v1.json")
    production = metadata["production"]
    development = metadata["development"]

    assert metadata["schemaVersion"] == 1
    assert metadata["manifestVersion"] == 1
    assert isinstance(production, list)
    assert isinstance(development, list)
    assert production == sorted(production)
    assert development == ["local-file"]
    assert set(production) | set(development) == SOURCE_TYPES
    assert set(production).isdisjoint(development)


def test_manifest_schema_uses_only_production_source_types() -> None:
    schema = _json("luminesk-v1.schema.json")
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    source = definitions["source"]
    assert isinstance(source, dict)
    properties = source["properties"]
    assert isinstance(properties, dict)
    source_type = properties["type"]
    assert isinstance(source_type, dict)
    declared = source_type["enum"]
    assert isinstance(declared, list)

    metadata = _json("supported-source-types-v1.json")
    production = metadata["production"]
    assert isinstance(production, list)
    assert set(declared) == set(production)
    assert "local-file" not in declared


def test_index_schema_matches_catalog_v1_root_contract() -> None:
    schema = _json("index-v1.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["indexVersion", "revision", "entries"]

    properties = schema["properties"]
    assert isinstance(properties, dict)
    index_version = properties["indexVersion"]
    assert isinstance(index_version, dict)
    assert index_version["const"] == 1

    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    entry = definitions["entry"]
    assert isinstance(entry, dict)
    assert entry["additionalProperties"] is False
    assert set(entry["required"]) == {
        "name",
        "displayName",
        "recipeVersion",
        "kind",
        "game",
        "edition",
        "summary",
        "keywords",
        "path",
        "manifestDigest",
    }
