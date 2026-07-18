---
sidebar_position: 7
---

# Cores & Upgrades

A **core** is the server engine distribution Luminesk-CLI downloads and runs.

## List available cores

```bash
nesk cores
```

Run `nesk diagnostic` first to validate provider availability.

## Choose core at creation time

```bash
nesk create --core nukkit --tag my-server --name "My Server" --dir ./servers/my
```

If `--core` is omitted, Luminesk-CLI prompts interactively.

## Upgrade core

```bash
nesk upgrade-core my-server
```

### Force redownload

```bash
nesk upgrade-core my-server --redownload
```

Use this when a server lacks stored hash metadata or when you want to force refresh.

## Core upgrade workflow

1. Ensure server is stopped.
2. Run `nesk upgrade-core <tag>`.
3. Start server again.
4. Validate logs via `nesk attach <tag>`.

## Change runtime image

```bash
nesk change-image my-server --image eclipse-temurin:17-jre
```

Image names are validated; invalid or non-existent images fail early.

## Limitations

- Core upgrade/image change operations require a modifiable (stopped) server state.
- Provider outages can block downloads/upgrades; see [Troubleshooting](/docs/troubleshooting).
