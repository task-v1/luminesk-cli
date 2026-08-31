---
sidebar_position: 3
---

# Migrating from 1.x to 2.0

Luminesk 2.0 is a clean format boundary. It does not read or convert the 1.x
configuration, registry, server metadata, or instance layout. Migration is a
side-by-side reinstall followed by an explicit copy of user-owned server data.
There is no supported in-place upgrade.

## Before you begin

Keep the 1.x executable or environment until the migration is verified. Record
the old instance path, server ports, core/version, runtime settings, and any
plugins or extensions. Make sure you know which paths contain worlds, player
data, allowlists, permissions, plugin data, and operator-edited configuration.

Stop the old server with the 1.x client and take a complete offline backup. For
example on Linux or macOS:

```bash
nesk stop OLD_TAG
cp -a /srv/minecraft/old-instance /srv/backups/old-instance-1.x
```

Use your platform's equivalent copy or snapshot mechanism. Verify that the
backup can be read before continuing. Do not delete or modify the original 1.x
instance during migration.

## Install a fresh 2.0 instance

Install Luminesk 2.0, check the environment, and select a reviewed 2.0 recipe
that matches the old server implementation:

```bash
uv tool install --force luminesk-cli==2.0.0
nesk doctor
nesk search
nesk info RECIPE
nesk install RECIPE --dir /srv/minecraft/new-instance --dry-run
nesk install RECIPE --dir /srv/minecraft/new-instance --yes
```

The new target must be empty. Never use the old instance directory as the
installation target, and do not copy 1.x Luminesk metadata into the new
instance.

## Move only user-owned data

Read the selected recipe's ownership and `[update].backup` declarations. Copy
only paths classified as `data` or `preserve`, such as worlds and explicitly
supported plugin or configuration directories. Do not copy these 1.x control
files into the new instance:

- Luminesk configuration, registry, state, lock, cache, or transaction files;
- generated launch scripts or runtime metadata;
- managed core binaries that the 2.0 recipe resolves itself;
- an entire old instance over the fresh 2.0 directory.

If the server implementation has its own version-specific world or plugin
migration procedure, follow that procedure before starting it under 2.0. A
Luminesk backup cannot make incompatible server data formats compatible.

## Validate and cut over

Validate the local contract before starting, then check readiness and logs:

```bash
nesk validate --dir /srv/minecraft/new-instance --instance
nesk start --dir /srv/minecraft/new-instance
nesk status --dir /srv/minecraft/new-instance
nesk validate --dir /srv/minecraft/new-instance --readiness
nesk logs --dir /srv/minecraft/new-instance
```

Confirm that worlds, permissions, plugins, ports, mounts, and backups behave as
expected. Keep the old server stopped while the new instance uses the same
ports. After acceptance, retain the offline 1.x backup according to your normal
retention policy.

## Roll back

If validation fails, stop the 2.0 instance and use the retained 1.x executable
to restart the untouched old instance or its verified backup. Do not try to
open a partially migrated 2.0 directory with the 1.x client. Investigate the
data copy or recipe mismatch, recreate a fresh 2.0 target, and repeat the
migration.

`nesk import` is only for rebuilding the 2.0 global index from valid 2.0 local
state. It is not a 1.x conversion command.
