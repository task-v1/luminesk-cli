---
sidebar_position: 2
---

# Getting Started

This guide explains what Luminesk-CLI manages and what you need before creating your first server.

## What Luminesk-CLI manages

Luminesk-CLI tracks each managed server by a **tag** and stores server metadata in a local SQLite-backed state database.

Each server record includes:

- server name and tag;
- filesystem path;
- selected core and downloaded executable metadata;
- runtime settings (Docker image, memory limit);
- runtime status metadata (running/stopped, PID, last start/stop).

## Requirements

- Python **3.13+** if you install from PyPI.
- Docker installed and accessible from your shell.

## Supported operating model

Luminesk-CLI is designed for:

- local development;
- private and small production-like deployments;
- multi-server operations from one CLI.

Luminesk-CLI is currently in **beta**. Validate your workloads before large production use.

## Verify your environment

Run:

```bash
nesk diagnostic
```

This checks core download/provider endpoints and exits non-zero when a source check fails.

## Next steps

- [Installation](/docs/installation)
- [Quick Start](/docs/quick-start)
- [Runtime & Docker Model](/docs/runtime-and-docker)
