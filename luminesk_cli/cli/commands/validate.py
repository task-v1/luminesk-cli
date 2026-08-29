from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from luminesk_cli.cli.commands.common import cache, emit, recipe, resolve_lock
from luminesk_cli.domain.errors import RuntimeOperationError, ValidationError
from luminesk_cli.domain.lockfile import LOCKFILE_NAME, load_lockfile
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import digest_file
from luminesk_cli.infrastructure.state import load_ownership, load_state


def run(namespace: Any) -> int:
    root, manifest = recipe(namespace.dir)
    phases = _phases(namespace)
    results = []
    lockfile = None

    if "static" in phases:
        results.append({"phase": "static", "ok": True})

    if "resolve" in phases or "build" in phases:
        lockfile = resolve_lock(root, manifest, frozen=False)
        results.append({"phase": "resolve", "ok": True})

    if "build" in phases:
        assert lockfile is not None

        with tempfile.TemporaryDirectory(prefix="nesk-validate-") as temporary:
            package = DeclarativeBuilder(cache()).build(
                manifest,
                lockfile,
                root,
                Path(temporary) / "validation.neskpkg",
            )
            results.append(
                {"phase": "build", "ok": True, "packageDigest": package.digest}
            )

    if "instance" in phases:
        _validate_instance(root, manifest.digest)
        results.append({"phase": "instance", "ok": True})

    if "readiness" in phases:
        state = load_state(root)

        if state is None or state.runtime.status != "running":
            raise RuntimeOperationError("instance is not running")

        if state.last_readiness_at is None:
            raise RuntimeOperationError("instance has no successful readiness result")

        results.append(
            {
                "phase": "readiness",
                "ok": True,
                "checkedAt": state.last_readiness_at,
            }
        )

    emit(
        namespace,
        {"validation": results},
        "Validation passed: "
        + ", ".join(str(item["phase"]) for item in results),
    )
    return 0


def _phases(namespace: Any) -> tuple[str, ...]:
    if namespace.all:
        return ("static", "resolve", "build", "instance", "readiness")

    for phase in ("static", "resolve", "build", "instance", "readiness"):
        if getattr(namespace, phase):
            dependencies = {
                "resolve": ("static", "resolve"),
                "build": ("static", "resolve", "build"),
            }
            return dependencies.get(phase, (phase,))

    return ("static",)


def _validate_instance(root: Path, manifest_digest: str) -> None:
    state = load_state(root)

    if state is None:
        raise ValidationError("instance state is missing")

    lockfile = load_lockfile(root / LOCKFILE_NAME)

    if lockfile.manifest_digest != manifest_digest:
        raise ValidationError("instance lock does not match manifest")

    if state.applied_lock_digest != lockfile.digest:
        raise ValidationError("instance state does not match applied lock")

    ledger = load_ownership(root)
    drift = []

    for path, entry in ledger.files.items():
        target = root / path

        if entry.digest is None:
            if not target.exists():
                drift.append(path)

            continue

        if not target.is_file() or target.is_symlink():
            drift.append(path)
            continue

        digest, _ = digest_file(target)

        if digest != entry.digest:
            drift.append(path)

    if drift:
        raise ValidationError("instance contains managed-file drift", drift=drift)
