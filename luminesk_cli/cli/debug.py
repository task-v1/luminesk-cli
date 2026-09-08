"""Opt-in stderr diagnostics for the command-line application."""

from __future__ import annotations

import logging
import sys
import traceback

LOGGER_NAME = "luminesk_cli"

_handler: logging.Handler | None = None
_previous_level: int | None = None
_previous_propagate: bool | None = None


def configure_debug(enabled: bool) -> None:
    """Enable or disable the CLI-owned debug handler without touching root logging."""

    global _handler, _previous_level, _previous_propagate

    logger = logging.getLogger(LOGGER_NAME)

    if enabled:
        if _handler is not None:
            return

        _previous_level = logger.level
        _previous_propagate = logger.propagate
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s DEBUG %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        _handler = handler
        return

    if _handler is None:
        return

    logger.removeHandler(_handler)
    _handler.close()
    _handler = None
    logger.setLevel(_previous_level if _previous_level is not None else logging.NOTSET)
    logger.propagate = _previous_propagate if _previous_propagate is not None else True
    _previous_level = None
    _previous_propagate = None


def log_exception_frames(logger: logging.Logger, exc: BaseException) -> None:
    """Log traceback coordinates without exception text, arguments, or locals."""

    frames = traceback.extract_tb(exc.__traceback__)
    logger.debug("failure exception_type=%s frames=%d", type(exc).__name__, len(frames))

    for frame in frames:
        logger.debug(
            "traceback file=%s line=%d function=%s",
            frame.filename,
            frame.lineno,
            frame.name,
        )
