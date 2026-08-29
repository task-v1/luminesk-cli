"""Backward-compatible import surface for the argparse CLI."""

from __future__ import annotations

from luminesk_cli.cli.entry import main


def app(argv: list[str] | None = None) -> int:
    """Compatibility callable retained for integrations importing ``app``."""

    return main(argv)


def init_cli_language() -> None:
    """Retained as a no-op; Nesk 2.0 renders stable plain output."""


__all__ = ["app", "init_cli_language", "main"]
