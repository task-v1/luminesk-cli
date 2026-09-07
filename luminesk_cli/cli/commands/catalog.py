from __future__ import annotations

import json
from typing import Any

from luminesk_cli.cli.commands.common import catalog_store, emit
from luminesk_cli.domain.catalog import CatalogEntry, search_catalog, suggest_catalog
from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.manifest import InputSpec
from luminesk_cli.infrastructure.catalog import CatalogClient


def search(namespace: Any) -> int:
    store = catalog_store()
    snapshot = store.load_active()
    matches = search_catalog(
        snapshot,
        namespace.query or "",
        kind=namespace.type,
        edition=namespace.edition,
    )
    if namespace.limit < 1:
        raise ValidationError("--limit must be at least 1")
    total = len(matches)
    if not namespace.all:
        matches = matches[: namespace.limit]
    suggestions = (
        suggest_catalog(snapshot, namespace.query or "") if not matches else ()
    )
    payload = {
        "revision": snapshot.revision,
        "catalogActivatedAt": store.activated_at(),
        "total": total,
        "returned": len(matches),
        "suggestions": list(suggestions),
        "recipes": [_payload(entry) for entry in matches],
    }
    if matches:
        plain = _search_table(matches)
        if total > len(matches):
            plain += (
                f"\nShowing {len(matches)} of {total}; use --all to show every match."
            )
    else:
        plain = "No recipes found."
        if suggestions:
            plain += " Did you mean: " + ", ".join(suggestions) + "?"
        plain += " Run `nesk catalog update` to refresh the catalog."
    plain += f"\nCatalog {snapshot.revision[:12]} activated {store.activated_at()}."
    emit(namespace, payload, plain, tone="info")
    return 0


def info(namespace: Any) -> int:
    store = catalog_store()
    snapshot = store.load_active()
    entry = next(
        (item for item in snapshot.entries if item.name == namespace.name), None
    )
    if entry is None:
        suggestions = suggest_catalog(snapshot, namespace.name)
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        raise ValidationError(f"catalog recipe not found: {namespace.name}.{hint}")
    manifest = CatalogClient(store).fetch_entry_manifest(snapshot, entry)
    data = _payload(entry)
    data["inputs"] = [_input_payload(spec) for spec in manifest.inputs]
    plain = (
        f"{entry.display_name}\n"
        f"Edition: {entry.edition}\n"
        f"Type: {entry.kind}\n"
        f"Recipe: {entry.recipe_version}\n"
        f"Platforms: {', '.join(entry.platforms) or 'not declared'}\n"
        f"License: {entry.license or 'not declared'}\n"
        f"Authors: {', '.join(entry.authors) or 'not declared'}\n"
        f"Sources: {', '.join(entry.source_types) or 'not indexed'}\n"
        f"Runtime image: {entry.runtime_image or 'not indexed'}\n"
        f"Repository: {entry.repository or 'not declared'}\n"
        f"{_input_text(manifest.inputs)}\n"
        f"Catalog: {snapshot.revision[:12]} (activated {store.activated_at()})\n"
        f"Install: nesk i {entry.name} --dir INSTANCE\n"
        f"{entry.summary}"
    )
    emit(
        namespace,
        {
            "revision": snapshot.revision,
            "catalogActivatedAt": store.activated_at(),
            "recipe": data,
        },
        plain,
        tone="info",
    )
    return 0


def update(namespace: Any) -> int:
    store = catalog_store()
    snapshot = CatalogClient(store).update()
    emit(
        namespace,
        {
            "revision": snapshot.revision,
            "indexDigest": snapshot.index_digest,
            "entries": len(snapshot.entries),
            "activatedAt": store.activated_at(),
        },
        f"Catalog updated to {snapshot.revision} ({len(snapshot.entries)} entries).",
    )
    return 0


def status(namespace: Any) -> int:
    store = catalog_store()
    if not store.active_path.is_file():
        emit(
            namespace,
            {"available": False},
            "Catalog is unavailable.",
            tone="warning",
        )
        return 0
    snapshot = store.load_active()
    emit(
        namespace,
        {
            "available": True,
            "revision": snapshot.revision,
            "indexDigest": snapshot.index_digest,
            "entries": len(snapshot.entries),
            "activatedAt": store.activated_at(),
        },
        f"Catalog {snapshot.revision}: {len(snapshot.entries)} entries "
        f"(activated {store.activated_at()}).",
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
        "license": entry.license,
        "authors": list(entry.authors),
        "platforms": list(entry.platforms),
        "repository": entry.repository,
        "sourceTypes": list(entry.source_types),
        "runtimeImage": entry.runtime_image,
    }


def _input_payload(spec: InputSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "type": spec.type,
        "required": spec.required,
        "secret": spec.secret,
        "default": spec.default,
        "prompt": spec.prompt,
        "minimum": spec.minimum,
        "maximum": spec.maximum,
        "pattern": spec.pattern,
        "option": "--set-file" if spec.secret else "--set",
    }


def _input_text(inputs: tuple[InputSpec, ...]) -> str:
    if not inputs:
        return "Inputs: none"

    lines = ["Inputs:"]
    for spec in inputs:
        requirement = "required" if spec.required else "optional"
        default = (
            "no default"
            if spec.default is None
            else f"default {json.dumps(spec.default, ensure_ascii=False)}"
        )
        lines.append(f"  {spec.name}: {spec.type}, {requirement}, {default}")
        if spec.prompt is not None:
            lines.append(f"    {spec.prompt}")
        constraints = []
        if spec.minimum is not None:
            constraints.append(f"minimum {spec.minimum}")
        if spec.maximum is not None:
            constraints.append(f"maximum {spec.maximum}")
        if spec.pattern is not None:
            constraints.append(f"pattern {spec.pattern}")
        if constraints:
            lines.append("    Constraints: " + ", ".join(constraints))
        option = "--set-file" if spec.secret else "--set"
        value = "PATH" if spec.secret else "VALUE"
        lines.append(f"    Supply: {option} {spec.name}={value}")
    return "\n".join(lines)


def _search_table(entries: tuple[CatalogEntry, ...]) -> str:
    rows = [
        (
            entry.name,
            entry.edition,
            entry.kind,
            entry.recipe_version,
            ",".join(entry.platforms) or "—",
            entry.summary,
        )
        for entry in entries
    ]
    headers = ("NAME", "EDITION", "TYPE", "VERSION", "PLATFORMS", "SUMMARY")
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers) - 1)
    ]

    def line(row: tuple[str, ...]) -> str:
        prefix = "  ".join(
            value.ljust(widths[index]) for index, value in enumerate(row[:-1])
        )
        return f"{prefix}  {row[-1]}"

    return "\n".join((line(headers), *(line(row) for row in rows)))
