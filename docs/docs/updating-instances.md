---
sidebar_position: 2
---

# Updating Instances

An update can change the tracked recipe, resolved server artifacts, runtime
image, templates, inputs, and managed files. Luminesk plans and applies those
changes transactionally, but production updates still require an independent
world backup, change review, and workload-specific acceptance.

## Recommended production workflow

### 1. Prepare recovery

- Confirm the instance is currently healthy with `status`, logs, and its real
  player/application checks.
- Take and verify an independent offline/snapshot backup of worlds, plugins,
  configs, and any external state.
- Confirm `[update].backup`, ownership, and retention cover transaction rollback.
- Schedule downtime. A running instance is stopped while the package changes.

```bash
nesk status --dir /srv/minecraft/example
nesk validate --dir /srv/minecraft/example --instance
nesk logs --dir /srv/minecraft/example
```

### 2. Refresh discovery when needed

For an official catalog recipe, update the catalog only when you want to
consider its newer entry:

```bash
nesk catalog update
nesk catalog status
nesk info RECIPE
```

A direct tracked GitHub branch resolves directly. Tags/commits and local recipe
snapshots do not adopt new recipe content, although mutable sources/images
inside them can still resolve differently.

### 3. Inspect available resolution changes

```bash
nesk outdated --dir /srv/minecraft/example
```

`outdated` obtains the candidate recipe according to its tracking policy,
resolves all sources and the runtime image, and compares them to the applied
lock. It reports recipe version/revision/content, source version/digest, and
runtime image changes. This is a connected operation.

### 4. Inspect recipe and local drift

```bash
nesk diff --dir /srv/minecraft/example
```

`diff` reports:

- changes to the installed canonical recipe/root manifest;
- upstream recipe/template additions, removals, changes, and bounded text diffs;
- modified/missing managed or generated instance files.

Resolve local managed-file drift before updating. There is no force flag that
silently overwrites it.

### 5. Preview the complete transaction

```bash
nesk update --dir /srv/minecraft/example --dry-run
nesk update --dir /srv/minecraft/example --dry-run --json --non-interactive
```

Preview resolves/acquires the candidate, populates verified caches, builds and
verifies a temporary package, and computes the install plan without modifying
the instance or stopping its container. The JSON result includes
`recipeChanges`, `packageChanges`, `securitySensitiveChanges`, and warnings;
use it when a reviewer needs the full structured result.

If required inputs are not persisted (especially secrets), supply them during
preview and apply:

```bash
nesk update --dir /srv/minecraft/example \
  --set memory=6g \
  --set-file rcon_password=/run/secrets/rcon-password \
  --dry-run
```

### 6. Apply and observe

```bash
nesk update --dir /srv/minecraft/example --yes
nesk status --dir /srv/minecraft/example
nesk logs --dir /srv/minecraft/example
nesk validate --dir /srv/minecraft/example --instance
nesk validate --dir /srv/minecraft/example --readiness
```

Use the same input overrides/files as the approved preview. `--yes` approves
the update summary; it does not bypass conflicts or verification. Leave time to
test login, world integrity, plugins, permissions, network paths, and backups.

## What apply does

Before touching the instance, the CLI has already acquired the candidate,
resolved its lock, built/verified a package, and produced a conflict-free plan.
Apply then:

1. records whether the current container is running and stops it if needed;
2. stages verified package and recipe content under `.luminesk_cli/`;
3. creates a transaction journal and backup;
4. applies create/replace/remove actions while preserving user-owned content;
5. runs `post-install` file checks;
6. commits the candidate recipe snapshot, root manifest, lock, ownership ledger,
   persisted non-secret inputs, package digest, and state;
7. if the old instance was running, starts the candidate and runs readiness;
8. only after success, prunes older backups to `retain_backups`.

If the instance was stopped before update, it remains stopped and readiness is
not run automatically. Start and validate it as an explicit acceptance step.

## What changes and what remains

| Item | Update behavior |
| --- | --- |
| Recipe | A tracked catalog entry/branch may supply a new exact snapshot. Pinned/local recipe content stays fixed. |
| Lock | Candidate manifest, target, source hashes/URLs, image digest, and recipe origin become the applied lock only through commit. |
| Source versions | Mutable provider selectors resolve again unless `--frozen`; component selection can retain other old source locks. |
| Managed/generated files | Replaced/removed only when current digest still matches the old ledger; drift conflicts. |
| Preserve/data paths | Existing content wins and old paths are not removed merely because a package stops declaring them. |
| Runtime container | Stopped before apply only if it was running; recreated from the candidate lock after commit. |
| Backup | Planned replacements/removals, declared backup paths, metadata, and recipe snapshot are saved under the transaction id. |

See [Ownership and User Data](/docs/ownership) for the exact decision table.

## Component updates

```bash
nesk update runtime --dir ./instance --dry-run
nesk update core --dir ./instance --dry-run
nesk update recipe --dir ./instance --dry-run
```

`runtime` selects the new runtime image while retaining old source locks. A
source id such as `core` selects only that new source among source locks.
`recipe` and an omitted component select the complete candidate lock. An
unknown component is rejected.

Component updates still bind the candidate manifest/recipe/build metadata and
build a complete package, so they are not arbitrary in-place file downloads.
Prefer a complete update unless a tested operational reason requires a narrow
component.

## Frozen updates and input-only rebuilds

```bash
nesk update --dir ./instance --frozen --dry-run
nesk update --dir ./instance --frozen --set memory=6g --yes
```

Frozen mode verifies the installed/cached recipe, exact lock, platform, origin,
and cached artifact hashes. It performs no new provider or recipe resolution.
This can reproduce package content or apply new non-secret/template inputs
against an existing lock, provided all required cached content is present. It
does not discover a new version.

## Automatic rollback

Apply/post-install failure restores the previous payload, manifest/recipe,
lock, ownership, and state. When a previously running instance fails candidate
start/readiness, Luminesk additionally stops/removes the candidate, restores the
transaction backup, and starts/checks the previous runtime.

The command reports a transaction error even when rollback succeeds, because
the requested update did not commit successfully. Confirm the old instance:

```bash
nesk status --dir ./instance
nesk logs --dir ./instance
nesk validate --dir ./instance --instance
```

If restoring files or the previous runtime also fails, stop making changes and
preserve `.luminesk_cli/transaction.json`, `backups/`, and readiness logs for
diagnosis.

## Manual recovery

Use recovery for an interrupted/incomplete transaction, not as a casual undo:

```bash
nesk status --dir ./instance
nesk stop --dir ./instance
nesk recover --dir ./instance
nesk validate --dir ./instance --instance
nesk start --dir ./instance
nesk logs --dir ./instance
```

If a journal identifies a transaction, `recover` uses that backup. Otherwise it
selects the newest retained backup. It reverses the saved install plan and
restores prior metadata/recipe state. It does not verify external databases or
application consistency and does not replace your independent backup.

If state is valid but the global instance index is missing, use `nesk import`;
that command does not recover files or convert legacy state.
