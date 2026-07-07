---
sidebar_position: 6
---

# Server Lifecycle

This guide describes operational workflows after server creation.

## First server setup flow

1. Run `nesk diagnostic`.
2. Create server with `nesk create ...`.
3. Start server: `nesk start <tag>`.
4. Attach logs if needed: `nesk attach <tag>`.
5. Verify status with `nesk list`.

## Daily operations flow

### Start

```bash
nesk start <tag>
```

Use `--detached` for background start.

### Attach logs

```bash
nesk attach <tag>
```

### Check state

```bash
nesk list
nesk list --status running
```

### Stop gracefully

```bash
nesk stop <tag>
```

### Kill forcefully

```bash
nesk kill <tag>
```

### Delete stopped server

```bash
nesk delete <tag>
```

Use `--yes` to skip interactive confirmation.

## Multi-server management flow

Filter by tag, status, and core:

```bash
nesk list --tag my-server
nesk list --status running
nesk list --core nukkit
```

## Target resolution behavior

Most runtime commands accept an optional tag:

- if omitted, Luminesk resolves by current directory;
- `stop` and `kill` can also target by PID.

## Loop mode safety

When started with `--loop`, server restarts automatically. Stopping loop-controlled servers may require `--force` depending on the exact control path.

See [Runtime & Docker Model](/docs/runtime-and-docker) for details.
