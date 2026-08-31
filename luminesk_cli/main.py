from importlib.metadata import PackageNotFoundError, version


def _detect_version() -> str:
    try:
        return version("luminesk_cli")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _detect_version()


def main() -> None:
    from luminesk_cli.cli.main import app, init_cli_language

    init_cli_language()
    app()


if __name__ == "__main__":
    main()
