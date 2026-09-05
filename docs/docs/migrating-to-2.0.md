---
sidebar_position: 3
---

# Migrating from Luminesk 1.x

Luminesk 2.0 introduced a clean compatibility boundary for recipes, locks,
instance state, ownership, and transactions. The current CLI therefore does not
read or convert a 1.x configuration, registry, server metadata, or instance
layout. Migration is a side-by-side install followed by an explicit copy of
user-owned server data. There is no supported in-place upgrade.

## Plan the cutover

Keep the 1.x executable or environment and the untouched old instance until the
new deployment is accepted. Record:

- old instance path and the command used to manage it;
- server implementation and exact version;
- ports, memory, container or Java settings;
- worlds, player data, allowlists, permissions, plugins, and plugin data;
- operator-edited configuration and secrets;
- file ownership and the backup/restore procedure.

Check the server implementation's own upgrade notes. World, plugin, or
configuration formats may require intermediate server versions; Luminesk cannot
make incompatible application data compatible.

## Stop and back up 1.x

Stop the server with the 1.x client or its existing service workflow. If your
old tag and command support this syntax, for example:

```bash
nesk stop OLD_TAG
```

Take a complete **offline** snapshot of the old instance. On Linux or macOS an
operator might use:

```bash
cp -a /srv/minecraft/old-instance /srv/backups/old-instance-1.x
```

Use the equivalent snapshot or backup system for your platform. Verify that the
backup can be listed and restored. Do not delete or modify the original 1.x
instance during the migration.

## Install the current CLI

Retain a callable copy of the 1.x environment for rollback, then follow the
normal [Installation](./installation.md) instructions. If uv already manages the
old package in the same tool slot, replace it without pinning an obsolete
release:

```bash
uv tool install --force luminesk-cli
nesk --version
nesk doctor
docker version
```

Normal installation always selects the current stable release. Do not add an
artificial `==2.0.0` pin: it would freeze the migration environment on the first
release of the format boundary rather than the supported current CLI.

## Select and review a current recipe

Find a recipe that matches the old server implementation and intended version:

```bash
nesk catalog update
nesk search QUERY
nesk info RECIPE
```

Review its sources, image, build code, inputs, mounts, ports, ownership rules,
checks, and update backups. If no suitable recipe exists, create and test one;
do not approximate a different server implementation just to complete the
migration.

## Install beside the old instance

Use a new empty destination, supply required inputs, and inspect the plan before
approval:

```bash
nesk install RECIPE --dir /srv/minecraft/new-instance --dry-run --yes
nesk install RECIPE --dir /srv/minecraft/new-instance --yes
```

`--yes` is needed here because even a dry-run of a remote recipe crosses the
recipe trust boundary. Never choose the old 1.x directory as the target. Do not
copy 1.x control metadata into the new directory.

## Copy only user-owned server data

Keep both servers stopped. Read the new recipe's ownership declarations and
`[update].backup` globs. Copy only paths classified as `data` or `preserve`, and
only when the server implementation documents them as portable. Typical
candidates are worlds, player data, allowlists, operator lists, supported plugin
directories, and explicitly operator-owned configuration.

Do **not** copy:

- the 1.x registry, configuration, state, lock, cache, or transaction files;
- the old generated launch scripts or runtime metadata;
- managed server binaries that the current recipe resolves itself;
- an entire old instance over the fresh current instance;
- plugins or configuration known to be incompatible with the selected server
  version.

Preserve numeric ownership and permissions deliberately when the container uses
`runtime.run_as`. After copying, confirm the container user can read and write
the declared data mounts without making them broadly world-writable.

## Validate before cutover

First validate the installed contract while stopped:

```bash
nesk validate --dir /srv/minecraft/new-instance --instance
nesk diff --dir /srv/minecraft/new-instance
```

Then start and evaluate readiness:

```bash
nesk start --dir /srv/minecraft/new-instance
nesk status --dir /srv/minecraft/new-instance
nesk validate --dir /srv/minecraft/new-instance --readiness
nesk logs --dir /srv/minecraft/new-instance
```

Keep the old server stopped when both deployments use the same host ports.
Verify worlds, player access, permissions, plugins, network exposure, saves,
stop/start behavior, and a real backup/restore drill. Acceptance should include
application-level checks, not just a running container.

## Cut over and observe

Switch clients, DNS, proxying, or firewall rules only after acceptance. Retain
the offline 1.x backup and old management environment according to a defined
rollback window. Monitor runtime logs, storage growth, memory use, save behavior,
and backup jobs through the first normal workload cycle.

## Roll back safely

If acceptance fails:

1. Stop the new instance.
2. Reverse any external routing change.
3. Restart the untouched old instance with the retained 1.x environment, or
   restore its verified offline backup.
4. Diagnose recipe, version, permission, or data-copy incompatibility.
5. Recreate a fresh current target and repeat the migration.

Do not open a partially migrated current directory with the 1.x client, and do
not copy data written by a newer incompatible server back into the old instance
without the server implementation's documented downgrade procedure.

`nesk import` is not a migration command. It only rebuilds the global index from
directories that already contain valid current Luminesk local state.
