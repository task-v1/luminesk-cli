from __future__ import annotations

from pathlib import Path
from typing import Any

from luminesk_cli.cli.commands.common import emit
from luminesk_cli.domain.catalog import CatalogEntry, load_catalog
from luminesk_cli.domain.errors import ValidationError


def search(namespace: Any) -> int:
    entries = _catalog(namespace.catalog)
    query = namespace.query.lower().strip() if namespace.query else ""
    requested_type = namespace.type
    matches = [
        entry
        for entry in entries
        if (requested_type is None or entry.type == requested_type)
        and (
            not query
            or query in entry.qualified_name.lower()
            or query in entry.description.lower()
        )
    ]
    payload = {"recipes": [_payload(entry) for entry in matches]}
    lines = [
        f"{entry.qualified_name} [{entry.trust}] — {entry.description}"
        for entry in matches
    ]
    emit(namespace, payload, "\n".join(lines) if lines else "No recipes found.")
    return 0


def info(namespace: Any) -> int:
    entries = _catalog(namespace.catalog)
    exact = [
        entry
        for entry in entries
        if namespace.name in {entry.name, entry.qualified_name}
    ]

    if not exact:
        raise ValidationError(f"catalog recipe not found: {namespace.name}")

    if len(exact) > 1:
        raise ValidationError(
            "catalog name is ambiguous; use NAMESPACE/NAME",
            matches=[entry.qualified_name for entry in exact],
        )

    entry = exact[0]
    data = _payload(entry)
    plain = (
        f"{entry.qualified_name}\n"
        f"Trust: {entry.trust}\n"
        f"Repository: {entry.repository}\n"
        f"Manifest: {entry.manifest}\n"
        f"Maintainers: {', '.join(entry.maintainers)}\n"
        f"License: {entry.license}\n"
        f"{entry.description}"
    )
    emit(namespace, {"recipe": data}, plain)
    return 0


def _catalog(value: str | None) -> tuple[CatalogEntry, ...]:
    directory = (
        Path(value).expanduser().resolve()
        if value is not None
        else Path(__file__).parents[2] / "community_catalog" / "recipes"
    )
    return load_catalog(directory)


def _payload(entry: CatalogEntry) -> dict[str, Any]:
    return {
        "name": entry.name,
        "namespace": entry.namespace,
        "qualifiedName": entry.qualified_name,
        "repository": entry.repository,
        "manifest": entry.manifest,
        "maintainers": list(entry.maintainers),
        "license": entry.license,
        "trust": entry.trust,
        "description": entry.description,
        "type": entry.type,
        "deprecated": entry.deprecated,
        "replacedBy": entry.replaced_by,
    }
