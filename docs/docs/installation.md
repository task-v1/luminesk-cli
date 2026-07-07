---
sidebar_position: 3
---

# Installation

## Option 1: One-line installer (recommended)

### Linux and macOS

```bash
curl -fsSL https://luminesk.taskov1ch.xyz/sh | sh
```

### Windows (PowerShell)

```powershell
iwr -useb https://luminesk.taskov1ch.xyz/ps1 | iex
```

## Option 2: Install from PyPI

```bash
pip install luminesk-cli
```

```bash
uv pip install luminesk-cli
```

```bash
pipx install luminesk-cli
```

## Option 3: Download prebuilt binaries

Download from [GitHub Releases](https://github.com/task-v1/luminesk-cli/releases/latest):

- `luminesk-windows-amd64.exe`
- `luminesk-windows-arm64.exe`
- `luminesk-linux-amd64`
- `luminesk-linux-arm64`
- `luminesk-darwin-amd64`
- `luminesk-darwin-arm64`

## Install from source

```bash
git clone https://github.com/task-v1/luminesk-cli
cd luminesk-cli

uv venv
uv sync

uv run nesk --help
```

## Verify installation

```bash
nesk --version
nesk --help
nesk diagnostic
```

If `diagnostic` fails, see [Troubleshooting](/docs/troubleshooting).
