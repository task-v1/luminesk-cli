---
sidebar_position: 4
---

# Quick Start

## 1) Check environment and providers

```bash
nesk diagnostic
```

## 2) Create your first server

```bash
nesk create -n "My Server" -d ./servers/my -c nukkit -t my-server
```

If you omit options, Luminesk-CLI prompts interactively.

## 3) Start the server

```bash
nesk start my-server
```

Or run from inside the server directory and omit the tag:

```bash
nesk start
```

## 4) Attach to logs

```bash
nesk attach my-server
```

## 5) List managed servers

```bash
nesk list
```

## 6) Stop and delete

```bash
nesk stop my-server
nesk delete my-server
```

## Common next tasks

- [Server Lifecycle](/docs/server-lifecycle)
- [Cores & Upgrades](/docs/cores-and-upgrades)
- [Command Reference](/docs/command-reference)
