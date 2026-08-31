from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from luminesk_cli.cli.entry import main
from luminesk_cli.domain.catalog import (
    CatalogEntry,
    CatalogSnapshot,
    parse_catalog_index,
    search_catalog,
)
from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.domain.manifest import parse_manifest
from luminesk_cli.domain.primitives import sha256_digest
from luminesk_cli.infrastructure.catalog import CatalogClient, CatalogStore
from luminesk_cli.infrastructure.template import read_template_tree

REVISION = "a" * 40


def _entry(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "name": "lumi",
        "displayName": "Lumi",
        "recipeVersion": "1.0.1",
        "kind": "core",
        "game": "minecraft",
        "edition": "bedrock",
        "summary": "Lumi Minecraft server",
        "keywords": ["lumi", "bedrock"],
        "path": "lumi",
        "manifestDigest": f"sha256:{'b' * 64}",
    }
    value.update(overrides)
    return value


def _index(*entries: dict[str, object], revision: str = REVISION) -> bytes:
    return (
        json.dumps(
            {
                "indexVersion": 1,
                "revision": revision,
                "entries": list(entries or (_entry(),)),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def test_index_is_strict_and_rejects_duplicate_or_escaping_entries() -> None:
    snapshot = parse_catalog_index(_index(_entry()))
    assert snapshot.revision == REVISION
    assert snapshot.entries[0].edition == "bedrock"

    with pytest.raises(ValidationError, match="duplicate"):
        parse_catalog_index(_index(_entry(), _entry()))
    with pytest.raises(ValidationError, match="path"):
        parse_catalog_index(_index(_entry(path="../lumi")))
    with pytest.raises(ValidationError, match="unknown key"):
        parse_catalog_index(_index(_entry(repository="https://attacker.example")))


def test_search_ranking_and_filters_are_deterministic() -> None:
    content = _index(
        _entry(),
        _entry(
            name="paper",
            displayName="Paper",
            edition="java",
            summary="High performance Java server",
            keywords=["paper", "java"],
            path="paper",
        ),
    )
    snapshot = parse_catalog_index(content)

    assert [entry.name for entry in search_catalog(snapshot, "paper")] == ["paper"]
    assert [entry.name for entry in search_catalog(snapshot, edition="bedrock")] == [
        "lumi"
    ]


def test_store_keeps_verified_active_snapshot_offline(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path / "catalog")
    content = _index(_entry())
    snapshot = parse_catalog_index(content)

    store.commit(snapshot, content)

    assert store.load_active() == snapshot
    assert store.verify() == snapshot
    assert store.use(REVISION) == snapshot


def test_store_rejects_immutable_revision_collision(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path / "catalog")
    content = _index(_entry())
    snapshot = parse_catalog_index(content)
    store.commit(snapshot, content)

    conflicting_content = _index(_entry(displayName="Changed"))
    conflicting_snapshot = parse_catalog_index(conflicting_content)
    with pytest.raises(SecurityError, match="collision"):
        store.commit(conflicting_snapshot, conflicting_content)

    assert store.load_active() == snapshot


def test_store_use_verifies_cached_snapshot_metadata(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path / "catalog")
    content = _index(_entry())
    snapshot = parse_catalog_index(content)
    store.commit(snapshot, content)
    index = tmp_path / "catalog" / "snapshots" / REVISION / "index-v1.json"
    index.write_bytes(_index(_entry(displayName="Tampered")))

    with pytest.raises(SecurityError, match="digest"):
        store.use(REVISION)


def test_catalog_update_verifies_digest_and_is_atomic(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path / "catalog")
    old_content = _index(_entry(), revision="b" * 40)
    old_snapshot = parse_catalog_index(old_content)
    store.commit(old_snapshot, old_content)
    new_content = _index(_entry())
    digest = hashlib.sha256(new_content).hexdigest()

    def valid_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/luminesk-database"):
            return httpx.Response(200, json={"default_branch": "main"})
        if request.url.path.endswith("/commits/main"):
            return httpx.Response(200, json={"sha": REVISION})
        if request.url.path.endswith(".sha256"):
            return httpx.Response(200, text=digest)
        return httpx.Response(200, content=new_content)

    client = httpx.Client(transport=httpx.MockTransport(valid_handler))
    updated = CatalogClient(
        store,
        client=client,
        allow_private_network=True,
    ).update()
    assert updated.revision == REVISION
    assert store.load_active() == updated

    bad_revision = "c" * 40

    def corrupt_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/luminesk-database"):
            return httpx.Response(200, json={"default_branch": "main"})
        if request.url.path.endswith("/commits/main"):
            return httpx.Response(200, json={"sha": bad_revision})
        if request.url.path.endswith(".sha256"):
            return httpx.Response(200, text="d" * 64)
        return httpx.Response(200, content=b"corrupt")

    with pytest.raises(SecurityError, match="digest"):
        CatalogClient(
            store,
            client=httpx.Client(transport=httpx.MockTransport(corrupt_handler)),
            allow_private_network=True,
        ).update()
    assert store.load_active() == updated


def test_search_info_and_catalog_status_emit_stable_json(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    root = tmp_path / "cache" / "luminesk_cli" / "v2" / "catalog"
    content = _index(_entry())
    CatalogStore(root).commit(parse_catalog_index(content), content)

    assert main(["search", "lumi", "--edition", "bedrock", "--json"]) == 0
    search = json.loads(capsys.readouterr().out)
    assert search["recipes"][0]["name"] == "lumi"
    assert "namespace" not in search["recipes"][0]

    assert main(["info", "lumi", "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["recipe"]["recipeVersion"] == "1.0.1"

    assert main(["catalog", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["available"] is True
    assert status["revision"] == REVISION


def test_catalog_entry_fetches_only_declared_template(tmp_path: Path) -> None:
    manifest_bytes = b"""\
manifest_version = 1
template = "template"
[package]
name = "lumi"
version = "1.0.1"
display_name = "Lumi"
kind = "core"
game = "minecraft"
edition = "bedrock"
summary = "Lumi Minecraft server"
keywords = ["lumi", "bedrock"]
[runtime]
image = "example/server:2"
command = ["./server"]
"""
    template_content = b"server-name=${input.server_name}\n"
    digest_root = tmp_path / "digest-recipe"
    (digest_root / "template").mkdir(parents=True)
    (digest_root / "luminesk.toml").write_bytes(manifest_bytes)
    (digest_root / "template/settings.yml.tmpl").write_bytes(template_content)
    manifest = parse_manifest(manifest_bytes)
    tree = read_template_tree(digest_root, manifest)
    assert tree is not None
    entry = CatalogEntry(
        name="lumi",
        display_name="Lumi",
        recipe_version="1.0.1",
        kind="core",
        game="minecraft",
        edition="bedrock",
        summary="Lumi Minecraft server",
        keywords=("lumi", "bedrock"),
        path="lumi",
        manifest_digest=sha256_digest(manifest_bytes),
        template_digest=tree.digest,
    )
    snapshot = CatalogSnapshot(
        revision=REVISION,
        entries=(entry,),
        index_digest=f"sha256:{'e' * 64}",
    )
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.host == "raw.githubusercontent.com":
            return httpx.Response(200, content=manifest_bytes)
        if "/contents/lumi/template" in request.url.path:
            return httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "path": "lumi/template/settings.yml.tmpl",
                        "size": len(template_content),
                        "download_url": "https://objects.example/settings.yml.tmpl",
                    }
                ],
            )
        return httpx.Response(200, content=template_content)

    recipe = CatalogClient(
        CatalogStore(tmp_path / "catalog"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        allow_private_network=True,
    ).acquire_entry(snapshot, entry, tmp_path / "recipe")

    assert recipe.origin.kind == "database"
    assert recipe.origin.entry == "lumi"
    assert (recipe.root / "template/settings.yml.tmpl").read_bytes() == template_content
    assert not any("src" in path or "tests" in path for path in requested_paths)
