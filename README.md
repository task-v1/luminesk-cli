<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli-dark.svg">
    <img src="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli-dark.svg" width="500" alt="Luminesk-CLI">
  </picture>

  <p><strong>A reproducible composer for Minecraft Bedrock server instances</strong></p>

  <p>
    <a href="https://github.com/task-v1/luminesk-cli/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/task-v1/luminesk-cli/ci.yml?branch=main&label=CI"></a>
    <a href="https://github.com/task-v1/luminesk-cli/releases/latest"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/task-v1/luminesk-cli"></a>
    <a href="https://pypi.org/project/luminesk-cli/"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/luminesk-cli"></a>
    <a href="https://github.com/task-v1/luminesk-cli/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/task-v1/luminesk-cli"></a>
    <a href="https://luminesk.taskov1ch.xyz"><img alt="Docs" src="https://img.shields.io/badge/docs-online-0ea5e9"></a>
  </p>
</div>

## Nesk 2.0

Luminesk-CLI (`nesk`) turns a declarative `luminesk.toml` recipe into a locked,
verified `.neskpkg`, applies it transactionally, and runs the instance in Docker.
Nesk 2.0 accepts only its current recipe, lockfile, package, and instance formats;
it does not read or convert earlier installations.

The important properties are:

- exact artifact hashes and OCI image digests in `luminesk.lock`;
- bounded downloads, archive extraction, and recipe checkouts;
- deterministic packages and explicit install/update plans;
- ownership-aware updates that preserve user data;
- rollback after failed installs, updates, or readiness checks;
- argv-only process execution—recipes cannot inject shell commands;
- stable `--json --non-interactive` behavior for automation.

## Install

Python 3.13+ and Docker are required. Git is not required for normal GitHub recipe
installs; Nesk uses the GitHub API and downloads an archive pinned to a commit.
Git is used only when `nesk install --keep-git` is requested.

```bash
uv tool install luminesk-cli
nesk --version
nesk doctor
```

Prebuilt onedir bundles for Linux, macOS, and Windows are published on the
[GitHub Releases](https://github.com/task-v1/luminesk-cli/releases/latest) page.

## Typical workflow

```bash
# Inspect recipes before trusting one.
nesk search
nesk info lumi

# Preview, confirm, and install a GitHub recipe without a local Git executable.
nesk install OWNER/RECIPE --dir ./servers/example --dry-run
nesk install OWNER/RECIPE --dir ./servers/example --yes

# Operate and update the instance.
nesk start --dir ./servers/example
nesk status --dir ./servers/example
nesk logs --dir ./servers/example
nesk outdated --dir ./servers/example
nesk update --dir ./servers/example --dry-run
```

For local recipe development:

```bash
nesk init --dir ./recipe --name example-server
nesk validate --dir ./recipe --static
nesk lock --dir ./recipe
nesk plan --dir ./recipe
```

See the [documentation](https://luminesk.taskov1ch.xyz), especially the
[command reference](https://luminesk.taskov1ch.xyz/docs/command-reference) and
[trust model](https://luminesk.taskov1ch.xyz/docs/recipes-and-updates).

## Development

```bash
uv sync --locked --extra dev
uv run python scripts/format.py --fix
uv run mypy .
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md). The project is beta software; validate
recipes and backups before production-critical use.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
