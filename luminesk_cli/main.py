from __future__ import annotations

from luminesk_cli._version import __version__ as __version__


def main(argv: list[str] | None = None) -> int:
    from luminesk_cli.cli.entry import main as entry_main

    return entry_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
