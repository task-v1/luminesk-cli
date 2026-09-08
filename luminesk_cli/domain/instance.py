"""Authoritative instance state and managed-file ownership ledger."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.primitives import (
    reject_unknown,
    require_int,
    require_keys,
    require_string,
    require_table,
    safe_relative_path,
    validate_digest,
)

STATE_VERSION = 1
OWNERSHIP_VERSION = 1


@dataclass(slots=True, frozen=True)
class RecipeState:
    kind: Literal["database", "github", "local"] | None = None
    source: str | None = None
    revision: str | None = None
    ref: str | None = None
    tracking: bool = False
    entry: str | None = None
    path: str | None = None
    version: str | None = None
    manifest_digest: str | None = None
    template_digest: str | None = None


@dataclass(slots=True, frozen=True)
class RuntimeState:
    driver: Literal["docker"] = "docker"
    container_id: str | None = None
    status: Literal["running", "stopped", "unknown"] = "stopped"


@dataclass(slots=True, frozen=True)
class InstanceState:
    instance_id: str
    name: str
    tag: str
    root: str
    applied_lock_digest: str
    installed_package_digest: str
    recipe: RecipeState
    inputs: dict[str, str | int | bool]
    runtime: RuntimeState
    created_at: str
    updated_at: str
    last_readiness_at: str | None = None
    pending_transaction: str | None = None
    state_version: int = STATE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "stateVersion": self.state_version,
            "instanceId": self.instance_id,
            "name": self.name,
            "tag": self.tag,
            "root": self.root,
            "appliedLockDigest": self.applied_lock_digest,
            "installedPackageDigest": self.installed_package_digest,
            "recipe": {
                "kind": self.recipe.kind,
                "source": self.recipe.source,
                "revision": self.recipe.revision,
                "entry": self.recipe.entry,
                "path": self.recipe.path,
                "ref": self.recipe.ref,
                "tracking": self.recipe.tracking,
                "version": self.recipe.version,
                "manifestDigest": self.recipe.manifest_digest,
                "templateDigest": self.recipe.template_digest,
            },
            "inputs": dict(sorted(self.inputs.items())),
            "runtime": {
                "driver": self.runtime.driver,
                "containerId": self.runtime.container_id,
                "status": self.runtime.status,
            },
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "lastReadinessAt": self.last_readiness_at,
            "pendingTransaction": self.pending_transaction,
        }


@dataclass(slots=True, frozen=True)
class OwnershipEntry:
    mode: Literal["managed", "preserve", "generated", "data"]
    digest: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "digest": self.digest}


@dataclass(slots=True, frozen=True)
class OwnershipLedger:
    files: dict[str, OwnershipEntry]
    ownership_version: int = OWNERSHIP_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "ownershipVersion": self.ownership_version,
            "files": {
                path: entry.to_dict() for path, entry in sorted(self.files.items())
            },
        }


def parse_state(content: bytes) -> InstanceState:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("instance state is not valid UTF-8 JSON") from exc

    table = require_table(value, "state")
    allowed = {
        "stateVersion",
        "instanceId",
        "name",
        "tag",
        "root",
        "appliedLockDigest",
        "installedPackageDigest",
        "recipe",
        "inputs",
        "runtime",
        "createdAt",
        "updatedAt",
        "lastReadinessAt",
        "pendingTransaction",
    }
    reject_unknown(table, allowed, "state")
    require_keys(table, allowed, "state")
    version = require_int(table["stateVersion"], "state.stateVersion")

    if version != STATE_VERSION:
        raise ValidationError(f"unsupported state version {version}")

    recipe_table = require_table(table["recipe"], "state.recipe")
    recipe_keys = {
        "kind",
        "source",
        "revision",
        "entry",
        "path",
        "ref",
        "tracking",
        "version",
        "manifestDigest",
        "templateDigest",
    }
    legacy_recipe = set(recipe_table) == {"source", "revision"}
    reject_unknown(recipe_table, recipe_keys, "state.recipe")
    if not legacy_recipe:
        require_keys(recipe_table, recipe_keys, "state.recipe")
    runtime_table = require_table(table["runtime"], "state.runtime")
    reject_unknown(runtime_table, {"driver", "containerId", "status"}, "state.runtime")
    require_keys(runtime_table, {"driver", "containerId", "status"}, "state.runtime")
    driver = require_string(runtime_table["driver"], "state.runtime.driver")
    status = require_string(runtime_table["status"], "state.runtime.status")

    if driver != "docker":
        raise ValidationError("state.runtime.driver must be docker")

    if status not in {"running", "stopped", "unknown"}:
        raise ValidationError("state.runtime.status is invalid")

    inputs_table = require_table(table["inputs"], "state.inputs")
    inputs: dict[str, str | int | bool] = {}

    for name, input_value in inputs_table.items():
        if not isinstance(input_value, (str, int, bool)):
            raise ValidationError(f"state.inputs.{name} has an invalid value")

        inputs[name] = input_value

    recipe_kind = (
        _optional_nullable_string(recipe_table, "kind", "state.recipe")
        if not legacy_recipe
        else None
    )
    if recipe_kind not in {None, "database", "github", "local"}:
        raise ValidationError("state.recipe.kind is invalid")
    recipe_tracking = recipe_table.get("tracking", False)
    if not isinstance(recipe_tracking, bool):
        raise ValidationError("state.recipe.tracking must be a boolean")

    return InstanceState(
        instance_id=require_string(table["instanceId"], "state.instanceId"),
        name=require_string(table["name"], "state.name"),
        tag=require_string(table["tag"], "state.tag"),
        root=require_string(table["root"], "state.root"),
        applied_lock_digest=validate_digest(
            table["appliedLockDigest"], "state.appliedLockDigest"
        ),
        installed_package_digest=validate_digest(
            table["installedPackageDigest"], "state.installedPackageDigest"
        ),
        recipe=RecipeState(
            kind=recipe_kind,  # type: ignore[arg-type]
            source=_optional_nullable_string(recipe_table, "source", "state.recipe"),
            revision=_optional_nullable_string(
                recipe_table, "revision", "state.recipe"
            ),
            entry=_recipe_optional(recipe_table, "entry", legacy_recipe),
            path=_recipe_optional(recipe_table, "path", legacy_recipe),
            ref=_recipe_optional(recipe_table, "ref", legacy_recipe),
            tracking=recipe_tracking,
            version=_recipe_optional(recipe_table, "version", legacy_recipe),
            manifest_digest=_recipe_optional_digest(
                recipe_table, "manifestDigest", legacy_recipe
            ),
            template_digest=_recipe_optional_digest(
                recipe_table, "templateDigest", legacy_recipe
            ),
        ),
        inputs=inputs,
        runtime=RuntimeState(
            driver="docker",
            container_id=_optional_nullable_string(
                runtime_table, "containerId", "state.runtime"
            ),
            status=status,  # type: ignore[arg-type]
        ),
        created_at=require_string(table["createdAt"], "state.createdAt"),
        updated_at=require_string(table["updatedAt"], "state.updatedAt"),
        last_readiness_at=_optional_nullable_string(table, "lastReadinessAt", "state"),
        pending_transaction=_optional_nullable_string(
            table, "pendingTransaction", "state"
        ),
    )


def parse_ownership(content: bytes) -> OwnershipLedger:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("ownership ledger is not valid UTF-8 JSON") from exc

    table = require_table(value, "ownership")
    reject_unknown(table, {"ownershipVersion", "files"}, "ownership")
    require_keys(table, {"ownershipVersion", "files"}, "ownership")
    version = require_int(table["ownershipVersion"], "ownership.ownershipVersion")

    if version != OWNERSHIP_VERSION:
        raise ValidationError(f"unsupported ownership version {version}")

    raw_files = require_table(table["files"], "ownership.files")
    files = {}

    for raw_path, raw_entry in raw_files.items():
        path = safe_relative_path(raw_path, f"ownership.files.{raw_path}")
        entry = require_table(raw_entry, f"ownership.files.{path}")
        reject_unknown(entry, {"mode", "digest"}, f"ownership.files.{path}")
        require_keys(entry, {"mode", "digest"}, f"ownership.files.{path}")
        mode = require_string(entry["mode"], f"ownership.files.{path}.mode")

        if mode not in {"managed", "preserve", "generated", "data"}:
            raise ValidationError(f"invalid ownership mode for {path}")

        digest = entry["digest"]

        if digest is not None:
            digest = validate_digest(digest, f"ownership.files.{path}.digest")

        files[path] = OwnershipEntry(
            mode=mode,  # type: ignore[arg-type]
            digest=digest,
        )

    return OwnershipLedger(files=files)


def _optional_nullable_string(table: dict[str, Any], key: str, path: str) -> str | None:
    value = table[key]

    if value is None:
        return None

    return require_string(value, f"{path}.{key}")


def _recipe_optional(table: dict[str, Any], key: str, legacy: bool) -> str | None:
    if legacy:
        return None
    return _optional_nullable_string(table, key, "state.recipe")


def _recipe_optional_digest(
    table: dict[str, Any], key: str, legacy: bool
) -> str | None:
    value = _recipe_optional(table, key, legacy)
    return validate_digest(value, f"state.recipe.{key}") if value is not None else None
