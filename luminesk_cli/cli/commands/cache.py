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
