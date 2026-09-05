---
sidebar_position: 4
---

# Quick Start

This walkthrough assumes `lumi` appears in your catalog search. Substitute a
different reviewed core recipe when needed.

## 1. Install and check the environment

```bash
uv tool install luminesk-cli
nesk --version
nesk doctor
docker version
```

## 2. Discover and inspect

```bash
nesk catalog update
nesk catalog status
nesk search --type core
nesk search lumi --type core
nesk info lumi
```

Catalog entries are discovery metadata, not an automatic trust decision. Open
the referenced recipe repository and inspect `luminesk.toml` and any declared
Dockerfile.

## 3. Preview and install

```bash
nesk install lumi --dir ./servers/example --dry-run
nesk install lumi --dir ./servers/example --yes
```

An official catalog name installs the exact recipe associated with the active
catalog entry. For a direct GitHub recipe, use `OWNER/RECIPE@REF` or
`--ref REF` to select a branch, tag, or commit. The installed lockfile records
the exact commit. The target must be empty for a remote or external local
recipe.

`--dry-run` resolves, builds, and prints the transaction plan without applying
it; remote recipes still require trust confirmation. `--yes` accepts the
displayed trust summary, so use it only after reviewing the recipe and plan.

## 4. Run the instance

```bash
nesk start --dir ./servers/example
nesk status --dir ./servers/example
nesk logs --dir ./servers/example
nesk stop --dir ./servers/example
```

When inside the instance directory, `--dir` may be omitted. `start` waits for
declared readiness checks unless `--no-wait` is explicitly provided.

## 5. Preview an update

```bash
nesk outdated --dir ./servers/example
nesk diff --dir ./servers/example
nesk update --dir ./servers/example --dry-run
nesk update --dir ./servers/example --yes
```

An update stops a running instance, applies the planned package transaction,
starts it again, waits for readiness, and restores the previous instance if a
required step fails. Keep independent backups for production data even though
the recipe also declares transaction backup paths.

If an interrupted transaction cannot recover automatically, run:

```bash
nesk recover --dir ./servers/example
nesk validate --dir ./servers/example --instance
```

Next, read [Server Lifecycle](/docs/server-lifecycle) and
[Recipes and Updates](/docs/recipes-and-updates). Recipe authors can continue
with [Manifest and Lockfile](/docs/manifest-and-lockfile).
