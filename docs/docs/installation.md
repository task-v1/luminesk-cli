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
```

Upgrade the tool with:

```bash
uv tool upgrade luminesk-cli
```

## Prebuilt bundle

Each tagged release publishes an onedir ZIP for these targets:

- `nesk-linux-amd64.zip`
- `nesk-linux-arm64.zip`
- `nesk-macos-amd64.zip`
- `nesk-macos-arm64.zip`
- `nesk-windows-amd64.zip`
- `nesk-windows-arm64.zip`

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

The CLI itself does not require Git. If `doctor` reports Git as missing, normal
GitHub installs still work; do not pass `--keep-git`.
