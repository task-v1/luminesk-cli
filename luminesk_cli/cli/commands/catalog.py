from __future__ import annotations

from typing import Any

from luminesk_cli.cli.commands.common import catalog_store, emit
from luminesk_cli.domain.catalog import CatalogEntry, search_catalog
from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.infrastructure.catalog import CatalogClient


def search(namespace: Any) -> int:
    snapshot = catalog_store().load_active()
    matches = search_catalog(
        snapshot,
        namespace.query or "",
        kind=namespace.type,
        edition=namespace.edition,
    )
    payload = {
        "revision": snapshot.revision,
        "recipes": [_payload(entry) for entry in matches],
    }
    lines = [
        f"{entry.name} [{entry.edition}/{entry.kind}] — {entry.summary}"
        for entry in matches
    ]
    emit(namespace, payload, "\n".join(lines) if lines else "No recipes found.")
    return 0


def info(namespace: Any) -> int:
    snapshot = catalog_store().load_active()
    entry = next(
        (item for item in snapshot.entries if item.name == namespace.name), None
    )
    if entry is None:
        raise ValidationError(f"catalog recipe not found: {namespace.name}")
    data = _payload(entry)
    plain = (
        f"{entry.display_name}\n"
        f"Edition: {entry.edition}\n"
        f"Type: {entry.kind}\n"
        f"Recipe: {entry.recipe_version}\n"
        f"Install: nesk i {entry.name}\n"
        f"{entry.summary}"
    )
    emit(namespace, {"revision": snapshot.revision, "recipe": data}, plain)
    return 0


def update(namespace: Any) -> int:
    snapshot = CatalogClient(catalog_store()).update()
    emit(
        namespace,
        {
            "revision": snapshot.revision,
            "indexDigest": snapshot.index_digest,
            "entries": len(snapshot.entries),
        },
        f"Catalog updated to {snapshot.revision} ({len(snapshot.entries)} entries).",
    )
    return 0


def status(namespace: Any) -> int:
    store = catalog_store()
    if not store.active_path.is_file():
        emit(namespace, {"available": False}, "Catalog is unavailable.")
        return 0
    snapshot = store.load_active()
    emit(
        namespace,
        {
            "available": True,
            "revision": snapshot.revision,
            "indexDigest": snapshot.index_digest,
            "entries": len(snapshot.entries),
        },
        f"Catalog {snapshot.revision}: {len(snapshot.entries)} entries.",
    )
    return 0


def verify(namespace: Any) -> int:
    snapshot = catalog_store().verify()
    emit(
        namespace,
        {
            "valid": True,
            "revision": snapshot.revision,
            "indexDigest": snapshot.index_digest,
        },
        f"Catalog snapshot {snapshot.revision} is valid.",
    )
    return 0


def use(namespace: Any) -> int:
    snapshot = catalog_store().use(namespace.revision)
    emit(
        namespace,
        {
            "revision": snapshot.revision,
            "indexDigest": snapshot.index_digest,
        },
        f"Using catalog snapshot {snapshot.revision}.",
    )
    return 0


def _payload(entry: CatalogEntry) -> dict[str, Any]:
    return {
        "name": entry.name,
        "displayName": entry.display_name,
        "recipeVersion": entry.recipe_version,
        "kind": entry.kind,
        "game": entry.game,
        "edition": entry.edition,
        "summary": entry.summary,
        "keywords": list(entry.keywords),
        "path": entry.path,
        "manifestDigest": entry.manifest_digest,
        "templateDigest": entry.template_digest,
    }
