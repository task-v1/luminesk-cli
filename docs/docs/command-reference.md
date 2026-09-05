---
sidebar_position: 5
---

# Command Reference

The public entry point is `nesk`:

```text
nesk [-h] [-v | --version] COMMAND ...
```

`nesk --version` prints the installed version. `nesk` with no command prints
help. Run `nesk COMMAND --help` or `nesk catalog COMMAND --help` for parser help
from the installed release.

## Shared automation options

Every leaf command accepts:

| Flag | Meaning |
| --- | --- |
| `--json` | Emit one stable JSON result instead of human-oriented output. |
| `--non-interactive` | Never read from stdin; a required choice becomes an error. |

`--non-interactive` does not approve trust. A remote install or an applied
update also needs `--yes`. `attach` is the exception in practice: the parser
accepts the shared flags, but the command rejects both because attaching is
inherently interactive. `logs --follow` similarly rejects `--json`.

Successful JSON objects contain `"ok": true`. A handled error has this shape:

```json
{
  "ok": false,
  "error": {
    "code": "validation",
    "message": "...",
    "details": {}
  }
}
```

The process exit codes are stable:

| Code | JSON error name | Meaning |
| ---: | --- | --- |
| `0` | — | Success. |
| `2` | `usage` | Command-line usage error produced by the argument parser. |
| `3` | `validation` | Invalid manifest, lock, package, input, or instance. |
| `4` | `resolution` | A version, artifact, recipe, or image could not be resolved. |
| `5` | `network` | A bounded network request failed. |
| `6` | `security` | Content violated a trust or safety boundary. |
| `7` | `conflict` | Confirmation is missing or user-owned state would be overwritten. |
| `8` | `runtime` | A Docker lifecycle operation failed. |
| `9` | `transaction` | An install/update transaction failed. |
| `10` | `internal` | Unexpected internal failure. |
| `130` | — | Interrupted with Ctrl+C. |

## Recipe authoring and validation

### `nesk init`

```text
nesk init [--dir DIR] [--name NAME] [--json] [--non-interactive]
```

Creates a starter `luminesk.toml`. `--dir` defaults to `.`. `--name` defaults
to the lowercase directory name with spaces replaced by hyphens. The command
refuses to replace an existing manifest and requires a lowercase package
identifier.

The generated source URL is deliberately a placeholder. Edit the manifest
before attempting resolution.

### `nesk validate`

```text
nesk validate [--dir DIR]
  [--static | --resolve | --build | --instance | --readiness | --all]
  [--json] [--non-interactive]
```

`--dir` defaults to `.`. With no level, validation is static.

| Level | Work performed |
| --- | --- |
| `--static` | Parse the strict manifest and validate its local schema. |
| `--resolve` | Static validation, provider resolution, artifact fetch/hash, and image pinning. |
| `--build` | Static + resolve, then build and verify a temporary `.lumineskpkg`. |
| `--instance` | Verify installed state, root marker, lock binding, ownership ledger, and managed-file digests. |
| `--readiness` | Run readiness checks against an already running instance. |
| `--all` | Run every level; therefore needs installed state and, for readiness, a running container. |

### `nesk lock`

```text
nesk lock [--dir DIR] [--frozen] [--json] [--non-interactive]
```

Resolves the recipe and crash-safely writes canonical `luminesk.lock` in
`DIR` (default `.`). It snapshots the local recipe identity into the lock.

`--frozen` does not regenerate resolution. It requires an existing lock whose
manifest digest, recipe origin, and target platform match, and whose artifacts
are present in the verified content cache.

### `nesk plan`

```text
nesk plan [--dir DIR] [--frozen]
  [--set KEY=VALUE]... [--set-file KEY=PATH]...
  [--json] [--non-interactive]
```

Builds a temporary package and prints the install/update changes without
applying them. `--dir` defaults to `.` and may be a recipe or installed
instance. On an instance, Luminesk plans from its verified canonical recipe
snapshot.

## Installation

### `nesk install` / `nesk i`

```text
nesk install [SOURCE] [--dir DIR] [--ref REF]
  [--set KEY=VALUE]... [--set-file KEY=PATH]...
  [--dry-run] [--frozen] [--yes] [--json] [--non-interactive]
```

Supported `SOURCE` forms are:

- an official catalog name such as `paper` or `db:paper`;
- an existing local recipe directory;
- `OWNER/REPO`, `github:OWNER/REPO`, or an HTTPS GitHub repository URL;
- any direct GitHub form above with `@REF`, or with `--ref REF`.

With no `SOURCE`, the recipe and target are `--dir` (default `.`). An external
local or remote recipe needs an empty target. `--ref` is valid only for a
direct GitHub recipe.

| Flag | Meaning |
| --- | --- |
| `--dir DIR` | Instance destination; defaults to the current directory. |
| `--set KEY=VALUE` | Set one declared non-secret input; repeatable. |
| `--set-file KEY=PATH` | Read a UTF-8 input from a file; repeatable and required for secret inputs. |
| `--dry-run` | Resolve, build, and show the plan without applying it. |
| `--frozen` | Use matching cached recipe/lock/artifacts only; perform no new resolution. |
| `--yes` | Accept the printed trust/capability/change preview. |

Remote and external local recipes require confirmation even for `--dry-run`,
because resolution and package building occur before the apply stage. Human and
JSON modes expose the same `Preview`: trust classification, exact recipe and
artifact identities, runtime/build capabilities, and every planned file change.
In automation, pass `--yes --non-interactive` only after approving that payload.

## Inspecting and applying updates

### `nesk outdated`

```text
nesk outdated [--dir DIR] [--json] [--non-interactive]
```

Resolves the tracked recipe, sources, and runtime image and reports changes
against the applied lock. This is a connected check; it has no frozen mode.

### `nesk diff`

```text
nesk diff [--dir DIR] [--json] [--non-interactive]
```

Shows three independent views: drift in the installed recipe snapshot,
upstream recipe/template changes, and local changes to managed/generated
instance files. A tracked remote recipe may require network access.

### `nesk update`

```text
nesk update [COMPONENT] [--dir DIR]
  [--set KEY=VALUE]... [--set-file KEY=PATH]...
  [--dry-run] [--frozen] [--yes] [--json] [--non-interactive]
```

Without `COMPONENT`, Luminesk resolves and applies the complete candidate
recipe and lock. `COMPONENT` may be `recipe`, `runtime`, or a source id from
`[[sources]]`; an unknown value is rejected. `recipe` selects the complete new
candidate lock, while `runtime` or a source id limits the resolved artifact
component retained in the mixed lock.

`--dry-run` performs the full planning path but does not stop or modify the
instance. `--frozen` uses the verified installed/cached recipe and the existing
lock and cache only. `--yes` is required to apply without a prompt. Existing
non-secret input values are reused; repeatable `--set`/`--set-file` options
override them for the candidate package.

### `nesk recover`

```text
nesk recover [--dir DIR] [--json] [--non-interactive]
```

Restores the transaction named by `.luminesk_cli/transaction.json`. If there is
no journal, it selects the newest retained backup. It errors when no recoverable
transaction exists. Validate and inspect the instance after recovery.

## Catalog

Catalog search and inspection are offline against the active verified snapshot.

### `nesk search`

```text
nesk search [QUERY] [--type {core,template}]
  [--edition {java,bedrock,cross-platform}] [--limit N | --all]
  [--json] [--non-interactive]
```

Searches names, display names, keywords, summaries, platforms, and source types.
Multiple query words must all match. An omitted query lists entries; output is
limited to 50 by default, while `--all` returns every match. Human output is a
table and JSON includes total/returned counts, suggestions, revision, and the
local catalog activation time.

### `nesk info`

```text
nesk info NAME [--json] [--non-interactive]
```

Shows one exact lowercase catalog entry from the active snapshot, including
kind, edition, recipe version, platforms, license, authors, repository, source
types, pinned runtime image, catalog freshness, and install name. Misspellings
include deterministic offline suggestions when available.

### `nesk catalog update`

```text
nesk catalog update [--json] [--non-interactive]
```

Downloads and verifies the latest official `task-v1/luminesk-database`
snapshot, then activates it crash-safely.

### `nesk catalog status`

```text
nesk catalog status [--json] [--non-interactive]
```

Reports whether a snapshot is active and, when available, its exact commit,
index digest, entry count, and local activation time. It exits successfully when
no catalog has been downloaded yet.

### `nesk catalog verify`

```text
nesk catalog verify [--json] [--non-interactive]
```

Re-parses the active cached index and verifies its pointer, repository,
revision, and SHA-256 binding.

### `nesk catalog use`

```text
nesk catalog use REVISION [--json] [--non-interactive]
```

Activates an already cached snapshot by its exact 40-character lowercase Git
commit. It does not download a missing revision.

## Runtime

For every runtime command, `--dir DIR` selects an instance directly. When it is
omitted, Luminesk searches the current directory and its parents for
`luminesk.toml`.

### `nesk start`

```text
nesk start [--dir DIR] [--set KEY=VALUE]...
  [--set-file KEY=PATH]... [--no-wait] [--json] [--non-interactive]
```

Creates the instance container from the locked image and normally waits for
readiness. Input overrides affect this start only; `--no-wait` skips readiness
and is intended for diagnosis.

### `nesk stop`

```text
nesk stop [--dir DIR] [--json] [--non-interactive]
```

Stops the recorded container using `[runtime].stop_timeout`. Docker receives
the manifest's stop signal when the container was created.

### `nesk restart`

```text
nesk restart [--dir DIR] [--set KEY=VALUE]...
  [--set-file KEY=PATH]... [--no-wait] [--json] [--non-interactive]
```

Runs stop followed by start and, unless `--no-wait` is set, readiness checks.

### `nesk status`

```text
nesk status [--dir DIR] [--json] [--non-interactive]
```

Inspects Docker and reconciles recorded state to `running` or `stopped`.

### `nesk logs`

```text
nesk logs [--dir DIR] [--follow | -f] [--json] [--non-interactive]
```

Prints Docker logs. `--follow` streams until interrupted and cannot be combined
with `--json`.

### `nesk attach`

```text
nesk attach [--dir DIR]
```

Attaches the terminal to the instance container with Docker signal proxying.
It rejects `--json` and `--non-interactive`.

## Diagnostics, cache, and instance discovery

### `nesk doctor`

```text
nesk doctor [--json] [--non-interactive]
```

Checks whether the Docker executable is on `PATH` and whether the current user
can contact the daemon. Missing CLI, timeout, permission denial, or an
unreachable daemon produces the stable `runtime` error and exit code 8.

### `nesk cache verify`

```text
nesk cache verify [--json] [--non-interactive]
```

Hashes every content-addressed blob and reports corruption. Corrupt content is
not accepted by normal cache restoration.

### `nesk cache prune`

```text
nesk cache prune [--max-age DAYS] [--dry-run]
  [--json] [--non-interactive]
```

Removes regular cached blobs at least `DAYS` old. `--max-age` is an integer and
defaults to `30`; negative values are rejected. `--dry-run` reports count and
bytes without deleting them. Blobs locked by another process are skipped.

### `nesk import`

```text
nesk import PATH [--scan] [--json] [--non-interactive]
```

Registers one valid local instance in the global index. With `--scan`, searches
below `PATH` for `.luminesk_cli/state.json` files and imports valid instance
roots (up to the built-in 10,000-state limit). This rebuilds discovery metadata;
it does not convert legacy instances.

## Input values

`--set` and `--set-file` may be repeated. Values are coerced according to the
declared `string`, `integer`, or `boolean` type; booleans accept only `true` or
`false`, case-insensitively. Duplicate and unknown names are errors.

`--set-file KEY=PATH` reads at most 64 KiB of UTF-8 and removes one trailing LF
or CRLF. Secret inputs must use this form. Secret values are not stored in
instance state and cannot be interpolated into runtime or readiness fields.

Example automation:

```bash
nesk validate --dir ./recipe --static --json --non-interactive
nesk install lumi --dir ./instance --dry-run --yes --json --non-interactive
nesk status --dir ./instance --json --non-interactive
```
