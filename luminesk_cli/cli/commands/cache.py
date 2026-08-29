from __future__ import annotations

from typing import Any

from luminesk_cli.cli.commands.common import cache, emit
from luminesk_cli.domain.errors import SecurityError


def verify(namespace: Any) -> int:
    count, corrupt = cache().verify()

    if corrupt:
        raise SecurityError(
            f"content cache contains {len(corrupt)} corrupt blob(s)",
            corrupt=list(corrupt),
        )

    emit(
        namespace,
        {"verified": count, "corrupt": []},
        f"Verified {count} cached blob(s).",
    )
    return 0


def prune(namespace: Any) -> int:
    count, size = cache().prune(
        max_age_seconds=namespace.max_age * 24 * 60 * 60,
        dry_run=namespace.dry_run,
    )
    verb = "Would remove" if namespace.dry_run else "Removed"
    emit(
        namespace,
        {"pruned": count, "bytes": size, "dryRun": namespace.dry_run},
        f"{verb} {count} cached blob(s), {size} byte(s).",
    )
    return 0
