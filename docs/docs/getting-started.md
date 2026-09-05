---
sidebar_position: 2
---

# Getting Started

## Requirements

- Python 3.13 or newer when using the Python package;
- Docker Engine or Docker Desktop for builds and runtime;
- outbound HTTPS access for remote recipes and artifacts.

Git is not required for installation or operation. A normal
`nesk install OWNER/REPO` resolves the requested ref through the GitHub API and
downloads only the bounded, declared content for the exact commit.

Run both environment checks after installation:

```bash
nesk doctor
docker version
```

`nesk doctor` confirms that the Docker command is on `PATH`. `docker version`
also confirms that the current user can reach the daemon. Docker is required
for runtime, mutable image resolution, and any declared recipe build.

## Choose a recipe and a destination

The verified official catalog is the normal starting point. Refresh it, filter
for a runnable core, and inspect the selected entry:

```bash
nesk catalog update
nesk search --type core
nesk search paper --edition java
nesk info RECIPE
```

`RECIPE` is the lowercase catalog name printed by `search`. Direct GitHub and
local recipes are also supported, but they have a different trust boundary.
Choose a new, empty directory for a remote install. One directory represents
one instance.

## What an instance contains

An installed instance keeps its contract beside the server files:

- `luminesk.toml` — reviewed recipe intent;
- `luminesk.lock` — exact source hashes, image digests, platform, and recipe
  revision;
- `.luminesk_cli/` — transaction journal, ownership ledger, backups, the
  canonical installed recipe snapshot, and runtime state.

Server payload files—such as `server.jar`, `server.properties`, `world/`, and
`plugins/`—also live in the instance according to the selected recipe. The
ownership policy determines which are managed by Luminesk and which remain
user data.

The global SQLite index is only a discovery aid. `nesk import PATH --scan` can
rebuild it from valid local instance state.

## Trust before install

Review the recipe source, declared build and network behavior, runtime image,
mounts, ports, generated files, and protected paths. Use `--dry-run` before the
first write and reserve `--yes` for a plan you have reviewed.

Continue with the [Quick Start](/docs/quick-start) for the complete install,
runtime, and update flow.
