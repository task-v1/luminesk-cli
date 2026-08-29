---
sidebar_position: 4
---

# Quick Start

## Discover and inspect

```bash
nesk doctor
nesk search
nesk search lumi --type core
nesk info lumi
```

Catalog entries are discovery metadata, not an automatic trust decision. Open
the referenced recipe repository and inspect `luminesk.toml` and any declared
Dockerfile.

## Preview and install

```bash
nesk install OWNER/RECIPE --dir ./servers/example --dry-run
nesk install OWNER/RECIPE --dir ./servers/example --yes
```

Use `OWNER/RECIPE@REF` or `--ref REF` to select a branch, tag, or commit. The
installed lockfile records the exact commit. The target must be empty for a
remote or external local recipe.

## Run the instance

```bash
nesk start --dir ./servers/example
nesk status --dir ./servers/example
nesk logs --dir ./servers/example
nesk stop --dir ./servers/example
```

When inside the instance directory, `--dir` may be omitted. `start` waits for
declared readiness checks unless `--no-wait` is explicitly provided.

## Preview an update

```bash
nesk outdated --dir ./servers/example
nesk diff --dir ./servers/example
nesk update --dir ./servers/example --dry-run
nesk update --dir ./servers/example --yes
```

If an interrupted transaction cannot recover automatically, run
`nesk recover --dir ./servers/example`.
