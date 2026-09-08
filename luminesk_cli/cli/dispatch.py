"""Lazy command handler loading and stable typed-error mapping."""

from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Callable
from typing import Any

from luminesk_cli.cli.parser import ParsedCommand

Handler = Callable[[Any], int]
LOGGER = logging.getLogger(__name__)


def dispatch(command: ParsedCommand) -> int:
    module_name, function_name = command.handler.split(":", 1)
    parsed_name = getattr(command.namespace, "command", None)
    command_name = parsed_name if isinstance(parsed_name, str) else "root"
    LOGGER.debug(
        "command started name=%s handler=%s.%s",
        command_name,
        module_name,
        function_name,
    )

    try:
        module = importlib.import_module(module_name)
        handler: Handler = getattr(module, function_name)
        exit_code = handler(command.namespace)
        LOGGER.debug("command completed name=%s exit_code=%d", command_name, exit_code)
        return exit_code
    except KeyboardInterrupt:
        LOGGER.debug("command interrupted name=%s", command_name)
        return 130
    except Exception as exc:
        from luminesk_cli.cli.debug import log_exception_frames
        from luminesk_cli.domain.errors import ErrorCode, LumineskError

        is_json = bool(getattr(command.namespace, "json", False))

        if isinstance(exc, LumineskError):
            code = exc.code
            details = exc.details
            message = exc.message
        else:
            code = ErrorCode.INTERNAL
            details = {}
            message = str(exc) or type(exc).__name__

        LOGGER.debug("command failed name=%s code=%s", command_name, code.name.lower())
        log_exception_frames(LOGGER, exc)

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
            from luminesk_cli.cli.output import print_error

            print_error(code.name.lower(), message, details=details)

        return int(code)
