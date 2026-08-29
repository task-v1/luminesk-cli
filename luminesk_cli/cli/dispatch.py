"""Lazy command handler loading and stable typed-error mapping."""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from typing import Any

from luminesk_cli.cli.parser import ParsedCommand

Handler = Callable[[Any], int]


def dispatch(command: ParsedCommand) -> int:
    module_name, function_name = command.handler.split(":", 1)

    try:
        module = importlib.import_module(module_name)
        handler: Handler = getattr(module, function_name)
        return handler(command.namespace)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        from luminesk_cli.domain.errors import ErrorCode, NeskError

        is_json = bool(getattr(command.namespace, "json", False))

        if isinstance(exc, NeskError):
            code = exc.code
            details = exc.details
            message = exc.message
        else:
            code = ErrorCode.INTERNAL
            details = {}
            message = str(exc) or type(exc).__name__

        if is_json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "code": code.name.lower(),
                            "message": message,
                            "details": details,
                        },
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            from luminesk_cli.cli.commands.common import sanitize

            print(f"error [{code.name.lower()}]: {sanitize(message)}")

        return int(code)
