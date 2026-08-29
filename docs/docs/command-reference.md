---
sidebar_position: 5
---

# Command Reference

Every non-interactive command supports `--json`. Commands that could prompt also
support `--non-interactive`; missing decisions then become stable errors rather
than reads from stdin.

| Command | Purpose |
| --- | --- |
| `init` | Create a strict recipe skeleton. |
| `validate` | Validate static, resolve, build, instance, or readiness contracts. |
| `lock` | Resolve sources and write canonical `luminesk.lock`. |
| `plan` | Build and show changes without applying them. |
| `install` / `i` | Install a local or GitHub recipe transactionally. |
| `outdated` | Compare the applied lock with currently resolvable inputs. |
| `diff` | Show managed-file drift and tracked recipe changes. |
| `update` | Apply recipe, source, or runtime updates transactionally. |
| `recover` | Restore an interrupted transaction from its journal or backup. |
| `cache verify` | Hash and verify every content-addressed cache blob. |
| `cache prune` | Remove cache entries older than `--max-age DAYS`. |
| `import` | Import one instance or rebuild the index with `--scan`. |
| `search` | Search the bundled or an alternate catalog. |
| `info` | Show one catalog entry. |
| `doctor` | Report Docker and optional Git availability. |
| `start` | Start Docker and wait for recipe readiness checks. |
| `stop` | Stop the instance container with the declared timeout. |
| `restart` | Stop, start, and check readiness. |
| `status` | Reconcile recorded and actual container status. |
| `logs` | Read logs; `--follow` occupies the terminal. |
| `attach` | Attach interactively to the running container. |

## Validation levels

```bash
nesk validate --dir ./recipe --static
nesk validate --dir ./recipe --resolve
nesk validate --dir ./recipe --build
nesk validate --dir ./instance --instance
nesk validate --dir ./instance --readiness
```

`--resolve` includes static validation. `--build` includes static and resolve.
`--all` runs every phase and therefore requires an installed, running instance
when readiness is declared.

## Install controls

- `SOURCE` accepts a local directory, `OWNER/REPO`, `github:OWNER/REPO`, or an
  HTTPS GitHub URL.
- `--ref REF` selects the recipe ref.
- `--set KEY=VALUE` supplies declared recipe inputs and may be repeated.
- `--dry-run` returns the install plan without writes.
- `--frozen` uses only the existing lock and content cache for local installs.
- `--keep-git` explicitly switches GitHub checkout to the local Git executable.
- `--yes` accepts the printed trust summary.

## Update controls

`nesk update COMPONENT` can select `recipe`, `runtime`, or a source id. Without
a component, the complete recipe and lock are updated. Always use `--dry-run`
before an unattended update.

## Automation example

```bash
nesk validate --dir ./recipe --static --json --non-interactive
nesk install OWNER/RECIPE --dir ./instance --dry-run --json --non-interactive
nesk status --dir ./instance --json --non-interactive
```

JSON errors contain a stable numeric code, error type, message, and structured
details. Plain output replaces control characters from untrusted values.
