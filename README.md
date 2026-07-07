<div align="center">
  <picture>
    <source
      media="(prefers-color-scheme: dark)"
      srcset="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli.svg">
    <source
      media="(prefers-color-scheme: light)"
      srcset="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli-dark.svg">
    <img
      src="https://github.com/task-v1/luminesk-cli/raw/refs/heads/main/docs/static/img/logo-with-cli.svg"
      width="500"
      alt="Luminesk CLI">
  </picture>

Composer of Minecraft Bedrock Edition (MCBE) servers

[![PyPI - Version](https://img.shields.io/pypi/v/luminesk-cli?style=for-the-badge)](https://pypi.org/project/luminesk-cli/) [![GitHub Release](https://img.shields.io/github/v/release/task-v1/luminesk-cli?style=for-the-badge)](https://github.com/task-v1/luminesk-cli/releases/latest) [![Tests](https://img.shields.io/github/actions/workflow/status/task-v1/luminesk-cli/ci.yml?style=for-the-badge)](https://github.com/task-v1/luminesk-cli/actions)

</div>

---

## Documentation

Canonical documentation lives at:

- **Website:** https://luminesk.taskov1ch.xyz
- **Docs source:** `/home/runner/work/luminesk-cli/luminesk-cli/docs/docs/`

Key sections:

- [Getting Started](https://luminesk.taskov1ch.xyz/docs/getting-started)
- [Installation](https://luminesk.taskov1ch.xyz/docs/installation)
- [Quick Start](https://luminesk.taskov1ch.xyz/docs/quick-start)
- [Command Reference](https://luminesk.taskov1ch.xyz/docs/command-reference)
- [Server Lifecycle](https://luminesk.taskov1ch.xyz/docs/server-lifecycle)
- [Cores & Upgrades](https://luminesk.taskov1ch.xyz/docs/cores-and-upgrades)
- [Configuration & Language](https://luminesk.taskov1ch.xyz/docs/configuration-and-language)
- [Runtime & Docker Model](https://luminesk.taskov1ch.xyz/docs/runtime-and-docker)
- [Troubleshooting](https://luminesk.taskov1ch.xyz/docs/troubleshooting)
- [FAQ](https://luminesk.taskov1ch.xyz/docs/faq)
- [Development & Contributing](https://luminesk.taskov1ch.xyz/docs/development-and-contributing)

---

## Quick install

### Linux & macOS

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

---

## Quick usage

```bash
nesk --help
nesk diagnostic
nesk create -n "My Server" -d ./servers/my -c nukkit -t my-server
nesk start my-server
nesk list
```

For full usage details, use the [Command Reference](https://luminesk.taskov1ch.xyz/docs/command-reference).

---

## Project status

Luminesk is in active **beta** development. Validate behavior in your own environment before production-critical usage.

---

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
