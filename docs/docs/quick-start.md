---
sidebar_position: 4
---

# Quick Start

This walkthrough uses the official `paper` recipe for Minecraft Java Edition.
The catalog also includes `lumi` for Bedrock Edition.

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
nesk search paper --type core --edition java
nesk info paper
```

Catalog entries are discovery metadata, not an automatic trust decision. Open
the referenced recipe repository and inspect `luminesk.toml` and any declared
Dockerfile.

## 3. Preview and install

```bash
nesk install paper --dir ./servers/example --set eula=true --dry-run --yes
nesk install paper --dir ./servers/example --set eula=true --yes
```

An official catalog name installs the exact recipe associated with the active
catalog entry. For a direct GitHub recipe, use `OWNER/RECIPE@REF` or
`--ref REF` to select a branch, tag, or commit. The installed lockfile records
the exact commit. The target must be empty for a remote or external local
recipe.

`--dry-run` resolves, builds, and prints the unified preview without applying
it. The preview includes trust, capabilities, pinned artifacts, runtime image,
and every planned file change. Remote recipes still require confirmation;
`--yes` accepts this exact preview. PaperMC also requires the explicit
`eula=true` input and never defaults acceptance on the user's behalf.

Official recipes default their non-root container identity to UID/GID 1000. On
Linux accounts with another identity, add
`--set runtime_uid=$(id -u) --set runtime_gid=$(id -g)` to the install command.

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
