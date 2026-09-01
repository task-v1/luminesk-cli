---
sidebar_position: 3
---

# Installation

## Isolated Python tool

With Python 3.13+ and uv installed:

```bash
uv tool install luminesk-cli
nesk --version
nesk doctor
nesk catalog update
```

Upgrade the tool with:

```bash
uv tool upgrade luminesk-cli
```

## Prebuilt bundle

Each tagged release publishes an onedir ZIP for these targets:

- `luminesk-linux-amd64.zip`
- `luminesk-linux-arm64.zip`
- `luminesk-macos-amd64.zip`
- `luminesk-macos-arm64.zip`
- `luminesk-windows-amd64.zip`
- `luminesk-windows-arm64.zip`

Download the matching archive from
[GitHub Releases](https://github.com/task-v1/luminesk-cli/releases/latest),
extract the complete directory, and place that directory on `PATH`. Do not move
only the executable; an onedir bundle needs its adjacent `_internal` files.

## Verify

```bash
nesk --version
nesk --help
nesk doctor
```

The CLI does not require Git. `doctor` reports the Docker dependency used for
runtime and mutable image resolution.
