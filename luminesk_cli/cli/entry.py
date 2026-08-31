"""Fast CLI entry point: version first, parser and handlers only on demand."""

from __future__ import annotations

import sys

from luminesk_cli._version import __version__


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv

    if arguments in (["--version"], ["-v"]):
        print(f"Luminesk {__version__}")
        return 0

    from luminesk_cli.cli.dispatch import dispatch
    from luminesk_cli.cli.parser import parse_command

    return dispatch(parse_command(arguments))
