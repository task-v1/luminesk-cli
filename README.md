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

[![PyPI - Version](https://img.shields.io/pypi/v/luminesk?style=for-the-badge)](https://pypi.org/project/luminesk/) [![GitHub Release](https://img.shields.io/github/v/release/task-v1/luminesk-cli?style=for-the-badge)](https://github.com/task-v1/luminesk-cli/releases/latest) [![Tests](https://img.shields.io/github/actions/workflow/status/task-v1/luminesk-cli/ci.yml?style=for-the-badge)](https://github.com/task-v1/luminesk-cli/actions)

</div>

---

# About the Project

**Luminesk** is a composer for **[Minecraft Bedrock Edition](https://minecraft.wiki/w/Bedrock_Edition)** servers.

The project is designed for:

- local server development
- small production deployments
- convenient management of multiple servers

Luminesk is maintained as a **CLI** (command-line interface) tool.

Supported engines: [Nukkit](https://github.com/CloudburstMC/Nukkit), [PowerNukkitX](https://github.com/PowerNukkitX/PowerNukkitX), [Nukkit-MOT](https://github.com/MemoriesOfTime/Nukkit-MOT), [Lumi](https://github.com/koshakminedev/lumi), and others.

---

# Features

- create servers
- start servers in **normal** and **loop mode**
- stop and force terminate servers
- manage server engines
- environment and provider diagnostics
- manage multiple servers
- update server engines

---

# Requirements

| Component | Version                        | Required                                        |
|-----------|--------------------------------|-------------------------------------------------|
| Python    | **3.13+**                      | Not required if you don't install from PyPI     |
| Docker    | latest                         | Required for running servers                    |

---

# Installation

## One-line installer (Recommended)

### Linux & macOS:
```bash
curl -fsSL https://luminesk.taskov1ch.xyz/sh | sh
```

### Windows (PowerShell):
```powershell
iwr -useb https://luminesk.taskov1ch.xyz/ps1 | iex
```

## Via [PyPI](https://pypi.org/project/luminesk/)

```bash
pip install luminesk
```

```bash
uv pip install luminesk
```

```bash
pipx install luminesk
```

---

## Download prebuilt binaries

Prebuilt binaries are available in the [releases](https://github.com/task-v1/luminesk-cli/releases) section:
* **Windows (x64)**: [luminesk-windows-amd64.exe](https://github.com/task-v1/luminesk-cli/releases/latest/download/luminesk-windows-amd64.exe)
* **Windows (ARM64)**: [luminesk-windows-arm64.exe](https://github.com/task-v1/luminesk-cli/releases/latest/download/luminesk-windows-arm64.exe)
* **Linux (x64)**: [luminesk-linux-amd64](https://github.com/task-v1/luminesk-cli/releases/latest/download/luminesk-linux-amd64)
* **Linux (ARM64)**: [luminesk-linux-arm64](https://github.com/task-v1/luminesk-cli/releases/latest/download/luminesk-linux-arm64)
* **macOS (Intel/x64)**: [luminesk-darwin-amd64](https://github.com/task-v1/luminesk-cli/releases/latest/download/luminesk-darwin-amd64)
* **macOS (Apple Silicon/ARM64)**: [luminesk-darwin-arm64](https://github.com/task-v1/luminesk-cli/releases/latest/download/luminesk-darwin-arm64)

---

# Installation from source

```bash
git clone https://github.com/task-v1/luminesk-cli
cd luminesk-cli

uv venv
uv sync

uv run nesk --help
```

## Building a binary

Uses **[PyInstaller](https://pyinstaller.org/)**.

Linux/macOS:

```bash
pyinstaller --onefile --name=luminesk \
  luminesk/__main__.py
```

The compiled binary will be available at `dist/luminesk`.

Windows:

```bash
pyinstaller --onefile --name=luminesk ^
  luminesk/__main__.py
```

The compiled binary will be available at `dist/luminesk.exe`.

---

# Quick Start

Show help:

```bash
nesk --help
```

Check environment and sources:

```bash
nesk diagnostic
```

Create a server:

```bash
nesk create -n "My Server" -d ./servers/my -c nukkit -t my-server
# Parameters are optional - Wizard Setup will start if omitted
```

Start a server:

```bash
nesk start my-server
# or run inside the server directory
```

Stop a server:

```bash
nesk stop my-server
```

List servers:

```bash
nesk list
```

---

# Runtime

Luminesk starts servers through **[Docker](https://www.docker.com/)**. Containers use `eclipse-temurin:21-jre` by default, mount the server directory into `/server`, use host networking on Linux and publish the default Bedrock port on Docker Desktop, and apply the server memory limit with Docker `--memory`.

Create a server with a custom background memory limit and Java runtime:

```bash
nesk create -n "My Server" -d ./servers/my -c nukkit -t my-server --memory 2g --java 21
```

`--java` accepts either a numeric version, such as `17` or `21`, or a full Docker image name, such as `eclipse-temurin:21-jre`.

Change Java for a stopped server:

```bash
nesk change-java --tag my-server --java eclipse-temurin:17-jre
```

Start and attach to logs immediately:

```bash
nesk start my-server
```

Start in the background:

```bash
nesk start my-server --detached
```

Follow container logs manually:

```bash
docker logs --follow luminesk-<server-tag>
```

---


# Warning
The project status of Luminesk is currently **active development (Beta)**. The tool is well-suited for small private servers and plugin development; however, at this stage, it is **not recommended for large commercial projects (Production)** without prior testing. Use it at your own risk.


---

# License

The project is licensed under **GPL-3.0-or-later**.

See [LICENSE](https://github.com/task-v1/luminesk-cli/blob/main/LICENSE)
