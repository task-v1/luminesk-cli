---
sidebar_position: 5
---

# Ownership and User Data

Ownership tells Luminesk which packaged paths it may replace and which paths
belong to the operator or server. The policy is recorded per package entry in
`.luminesk_cli/ownership.json`, together with the digest of each installed
regular file. That ledger—not a guess based on filenames—drives later plans.

## The four modes

| Mode | Typical use | Install/update behavior |
| --- | --- | --- |
| `managed` | Core binaries, immutable launch/config assets | Replace only when the current file still matches the digest Luminesk installed. |
| `generated` | Rendered files intended to follow recipe/input changes | Same digest conflict protection as managed; the distinct label explains provenance. |
| `preserve` | User-editable or server-created config such as `server.properties` | If a regular file already exists with different content, keep the existing copy. Never remove it merely because it leaves a later package. |
| `data` | Worlds, plugins, player data, databases | Preserve existing content and never remove it merely because it leaves a later package. Directory contents are not treated as managed children. |

Sources and Dockerfile output start as `managed`. Top-level template output
starts as `generated`. `[[files]].mode` selects a mode explicitly, and
`[ownership]` recursively overrides matching package paths.

## Declare server data

```toml
[[files]]
source = "data/world"
target = "world"
mode = "data"

[[files]]
source = "data/plugins"
target = "plugins"
mode = "data"

[ownership]
preserve = ["server.properties"]
data = ["world", "world_nether", "world_the_end", "plugins"]
```

A missing `[[files]].source` is normally an error. For `mode = "data"` only,
it creates an empty target directory. This is useful because source control
does not retain empty directories. If a seed directory exists, its regular
contents are packaged as data too.

Ownership paths are normalized literal prefixes, not globs. A policy for
`plugins` covers packaged `plugins/example/config.yml`. Duplicate paths and any
overlap between `preserve` and `data` are invalid. `executable` is a separate
mode policy:

```toml
[ownership]
executable = ["bin"]
```

It changes package file permissions but does not change update ownership.

## What happens during a plan

For each new package entry, Luminesk compares the target, new package digest,
and previous ownership ledger:

| Current state | Planned action |
| --- | --- |
| Path is absent | `create`. |
| Existing content already equals the new package | `preserve` because no write is needed. |
| Existing directory is a real directory | Preserve the directory; packaged child entries are planned independently. |
| New mode is `preserve` or `data` and a different regular file exists | Preserve the user's file. |
| Managed/generated file equals its previously recorded digest and package content changed | `replace`. |
| Managed/generated file differs from its ledger digest | `conflict`; do not overwrite. |
| A non-directory occupies a declared directory, or target is a link/special path | `conflict`. |

When a managed/generated file disappears from the new package, Luminesk
removes it only if it still matches the old ledger digest. A locally modified
copy is a conflict. Old preserve/data entries are left in place.

Preview these decisions before every production update:

```bash
nesk diff --dir ./instance
nesk plan --dir ./instance
nesk update --dir ./instance --dry-run
```

`diff` reports recipe drift, upstream recipe/template changes, and modified or
missing ledgered files. `plan` focuses on package actions. `update --dry-run`
also follows the complete update candidate and security-change path.

## Example: `server.properties`

Prefer letting the server create its complete configuration. Omit the file from
the template tree, reserve it for the operator, and include it in transaction
backups:

```toml
[ownership]
preserve = ["server.properties"]

[update]
backup = ["server.properties"]
```

Start the instance once, stop it, and edit the full file produced by the server.
Because no package entry claims the path, later packages leave it alone; the
preserve declaration also prevents a future package revision from taking over
an existing operator copy.

Templates are whole-file output, not property-level patches. Never seed only a
few `server.properties` lines: doing so prevents the server from creating its
complete defaults. If seeding is unavoidable, provide a complete
upstream-compatible file and mark it `preserve`. New recipe defaults will not
reach an existing operator copy automatically, so document any manual merge an
update requires.

If you instead leave the file `generated`, an update can replace it only while
the installed copy is untouched. A user edit becomes an explicit conflict,
which is preferable when silently keeping an old config would be unsafe.

## Example: worlds and plugins

Mark the top-level server-owned directories as data and include them in the
transaction backup list:

```toml
[ownership]
data = ["world", "world_nether", "world_the_end", "plugins"]

[update]
backup = ["world", "world_nether", "world_the_end", "plugins", "server.properties"]
retain_backups = 3
rollback_on_failure = true
```

The data mode prevents package replacement/removal. The backup declaration
copies existing real files/directories before changes are applied. These are
different protections and normally belong together.

Server-created files below a preserved data directory are not added one by one
to the ownership ledger. Luminesk preserves the directory and leaves its
contents to the server/operator.

## Transaction backups

Before apply, a transaction backup receives:

- files the plan will replace or remove;
- each existing non-symlink path in `[update].backup`;
- the previous lockfile, instance state, and ownership ledger;
- the root manifest and canonical recipe snapshot when present;
- the install plan needed to reverse create/replace/remove actions.

After a successful transaction, the newest `retain_backups` directories are
kept by modification time and older ones are removed. A value of `0` removes
all transaction backups after success. Failed operations attempt rollback
before pruning.

Luminesk always attempts rollback on install/update failure even
though `rollback_on_failure` is present in schema v1. Keep it `true` to express
the only supported operational expectation.

Transaction backups live under the instance `.luminesk_cli/backups/` state.
They protect one apply operation; they are not an independent, off-host, or
application-consistent backup strategy. Snapshot production worlds separately,
test restoration, and keep retention appropriate to the server.

## Resolving a managed-file conflict

When a plan says a managed file was modified outside Luminesk:

1. Stop and inspect it; do not delete the ledger or force an overwrite.
2. Save the local version outside the instance.
3. Decide whether it should become user-owned in the recipe, be restored to
   the applied content, or have its intentional changes incorporated into a
   new recipe version.
4. Update `[ownership]` or `[[files]].mode` when ownership was modeled
   incorrectly.
5. Rebuild/reinstall a test instance, then rerun `diff` and `update --dry-run`.

There is no force flag for bypassing ownership conflicts. That is deliberate:
the plan must become safe before the transaction starts.
