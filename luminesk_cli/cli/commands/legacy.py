from __future__ import annotations

from typing import Any


def run(namespace: Any) -> int:
    from luminesk_cli.cli.main import app, init_cli_language

    init_cli_language()
    app([namespace.legacy_command, *namespace.legacy_args])
    return 0
