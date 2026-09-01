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

Run the environment check after installation:

```bash
nesk doctor
```

Docker is reported as required for runtime and mutable image resolution.

## What an instance contains

An installed instance keeps its contract beside the server files:

- `luminesk.toml` — reviewed recipe intent;
- `luminesk.lock` — exact source hashes, image digests, platform, and recipe
  revision;
- `.luminesk_cli/` — transaction journal, ownership ledger, backups, and runtime
  state.

The global SQLite index is only a discovery aid. `nesk import PATH --scan` can
rebuild it from valid local instance state.

## Trust before install

Review the recipe source, declared build permission, network permission,
runtime image, mounts, ports, and protected paths. Use `--dry-run` before the
first write and reserve `--yes` for a plan you have reviewed.
