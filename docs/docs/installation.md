---
sidebar_position: 3
---

# Installation

Luminesk supports a one-line installer, Python tool installation, and
self-contained release bundles. Choose one installation method and keep using
the same method for updates; do not layer multiple managers over one `nesk`
executable.

## Requirements

- **Python 3.13 or newer** for `uv tool install`; release bundles include their
  own Python runtime.
- **Docker Engine or Docker Desktop** for running servers, resolving mutable
  image tags, and recipes that declare a Dockerfile build.
- **HTTPS access** while refreshing the catalog or resolving remote artifacts.

Git is not required for normal use. Luminesk acquires GitHub recipes through
the GitHub API, limits what it downloads, and pins the selected commit.

## Install with one command

The one-line installer downloads the self-contained binary, so Python is not
required.

On Linux or macOS:

```bash
curl -fsSL https://luminesk.taskov1ch.xyz/sh | sh -s -- --yes
```

On Windows, open PowerShell and run:

```powershell
irm https://luminesk.taskov1ch.xyz/ps1 | iex
```

The installer:

- detects the operating system and AMD64/ARM64 architecture;
- selects the matching asset from the latest GitHub release;
- requires a valid SHA-256 digest in the release metadata and verifies the
  download before installation;
- refuses to overwrite a `nesk` owned by uv, pipx, or a manual installation.

In the Unix command, `--yes` is an installer option: piping occupies standard
input, so the installer cannot ask its normal terminal question. This option
approves only installing the Luminesk executable. It does not accept the
Minecraft EULA, provide a recipe input, or approve a later `nesk install` or
`nesk update` plan. The PowerShell command asks before writing.

A normal Linux/macOS user installation goes to `~/.local/bin/nesk`; a root
installation uses `/usr/local/bin/nesk`. A normal Windows installation goes to
`$HOME\.local\bin\nesk.exe`; an Administrator installation uses
`$env:ProgramFiles\luminesk\nesk.exe`. If the installer warns that this
directory is missing from `PATH`, add it and open a new terminal.

Run the same one-line command later to check for and install an update. To
remove an installation owned by the script, use:

```bash
curl -fsSL https://luminesk.taskov1ch.xyz/sh | sh -s -- --delete --yes
```

```powershell
& ([scriptblock]::Create((irm https://luminesk.taskov1ch.xyz/ps1))) "--delete"
```

These commands execute a remote script over HTTPS. You can review the complete
[Linux/macOS installer](https://luminesk.taskov1ch.xyz/sh) or
[Windows installer](https://luminesk.taskov1ch.xyz/ps1) before running it.

## Install with uv

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

If the installation succeeds but the command is not found, run:

```bash
uv tool update-shell
```

Then open a new terminal. You can also follow uv's printed instruction and add
its tool binary directory to `PATH` manually.

## Install with pipx

With Python 3.13+ and pipx installed:

```bash
pipx install luminesk-cli
nesk --version
nesk doctor
```

Upgrade the isolated environment with:

```bash
pipx upgrade luminesk-cli
```

If `nesk` is not found, run `pipx ensurepath`, open a new terminal, and retry.
Use either uv or pipx to own the tool installation; do not layer both managers
over the same executable path.

## Prebuilt release bundles

Release bundles do not require a system Python. Each tagged release publishes
an onedir ZIP for these targets:

- `luminesk-linux-amd64.zip`
- `luminesk-linux-arm64.zip`
- `luminesk-macos-amd64.zip`
- `luminesk-macos-arm64.zip`
- `luminesk-windows-amd64.zip`
- `luminesk-windows-arm64.zip`

Download the matching archive and `SHA256SUMS` from
[GitHub Releases](https://github.com/task-v1/luminesk-cli/releases/latest),
verify its checksum, and extract it. The archive contains a `nesk` directory;
keep its executable and adjacent `_internal` directory together.

- On Linux or macOS, add the extracted `nesk` directory to your shell's `PATH`.
- On Windows, add the extracted `nesk` directory to the user `Path` in System
  Properties, then open a new PowerShell window.

The same release also contains standalone assets named
`luminesk_cli-linux-*`, `luminesk_cli-darwin-*`, and
`luminesk_cli-windows-*.exe`. The one-line installer uses those assets. Prefer
the ZIP when you want the transparent onedir layout, or uv when you want
Python-managed upgrades.

To upgrade a bundle, verify and extract the new complete bundle, then replace
the old bundle directory. Instances and the content cache are outside the
program directory.

## Platform notes

### Linux

Docker access is user-specific. `docker version` must succeed as the same user
that runs `nesk`. If Docker reports a permission error, follow your
distribution's Docker post-installation guidance or run Docker rootless.

Typical user-local binary directories include `~/.local/bin`. Add one to the
current shell, for example:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Persist the equivalent setting in your shell profile after confirming it.

### macOS

Start Docker Desktop before using image, build, or runtime operations. For uv,
restart the terminal after `uv tool update-shell`. For a bundle, add the
directory containing `nesk` to the shell `PATH` and keep `_internal` beside it.

### Windows

Use Python 3.13+ with uv, or download the `windows-amd64`/`windows-arm64`
bundle that matches the machine. After changing the user `Path`, start a new
PowerShell session and check resolution with:

```powershell
Get-Command nesk
nesk --version
```

Docker Desktop must be running and configured for Linux containers.

## Verify

```bash
nesk --version
nesk --help
nesk doctor
docker version
nesk catalog update
```

`doctor` checks both the Docker CLI and daemon connectivity; `docker version`
prints their detailed versions. The one-line installers stop if release
metadata, the matching asset digest, or a SHA-256 tool is unavailable; they
never install an unverified download. If a release bundle fails before `--version`,
compare its checksum with `SHA256SUMS`, remove the extracted copy, and extract
the entire archive again. See [Troubleshooting](/docs/troubleshooting) for PATH,
Docker, and damaged-download diagnostics.
