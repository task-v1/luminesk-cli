<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli-dark.svg">
    <img src="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli-dark.svg" width="500" alt="Luminesk-CLI">
  </picture>

  <p><strong>Composer of Minecraft Bedrock Edition (MCBE) servers</strong></p>

  <p>
    <a href="https://github.com/task-v1/luminesk-cli/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/task-v1/luminesk-cli/ci.yml?branch=main&label=CI"></a>
    <a href="https://github.com/task-v1/luminesk-cli/releases/latest"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/task-v1/luminesk-cli"></a>
    <a href="https://pypi.org/project/luminesk-cli/"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/luminesk-cli"></a>
    <a href="https://pypi.org/project/luminesk-cli/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/luminesk-cli"></a>
    <a href="https://github.com/task-v1/luminesk-cli/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/task-v1/luminesk-cli"></a>
    <a href="https://luminesk.taskov1ch.xyz"><img alt="Docs" src="https://img.shields.io/badge/docs-online-0ea5e9"></a>
  </p>
</div>

---

## What is Luminesk-CLI?

Luminesk-CLI (`nesk`) is a command-line tool for provisioning and operating MCBE servers.
It handles server creation, runtime configuration, downloads, updates, diagnostics, and lifecycle actions through one unified interface.

## Key capabilities

- Create and manage multiple MCBE server instances with stable tags.
- Download supported cores and update them when new versions are available.
- Run servers with a local Java runtime or Docker runtime.
- Validate environment and provider availability with diagnostics.
- Inspect server state, logs, and metadata from CLI commands.
- Use consistent commands across Linux, macOS, and Windows.

## Start here

- [Getting Started](https://luminesk.taskov1ch.xyz/docs/getting-started)
- [Installation](https://luminesk.taskov1ch.xyz/docs/installation)
- [Quick Start](https://luminesk.taskov1ch.xyz/docs/quick-start)
- [Command Reference](https://luminesk.taskov1ch.xyz/docs/command-reference)
- [Runtime & Docker Model](https://luminesk.taskov1ch.xyz/docs/runtime-and-docker)
- [Troubleshooting](https://luminesk.taskov1ch.xyz/docs/troubleshooting)

## Installation

### Linux / macOS

```bash
curl -fsSL https://luminesk.taskov1ch.xyz/sh | sh
```

### Windows (PowerShell)

```powershell
iwr -useb https://luminesk.taskov1ch.xyz/ps1 | iex
```

### PyPI

```bash
pip install luminesk-cli
```

## Quick start

```bash
nesk --help
nesk diagnostic
nesk create -n "My Server" -d ./servers/my -c nukkit -t my-server
nesk start my-server
nesk list
```

For full command behavior, use the [Command Reference](https://luminesk.taskov1ch.xyz/docs/command-reference).

## Development

- Contributor guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Documentation-specific contributor notes: [Development & Contributing](https://luminesk.taskov1ch.xyz/docs/development-and-contributing)

## Project status

Luminesk-CLI is in active **beta** development.
Validate behavior in your own environment before production-critical usage.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
