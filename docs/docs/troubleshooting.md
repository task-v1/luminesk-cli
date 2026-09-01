---
sidebar_position: 10
---

# Troubleshooting

## Docker is missing or unavailable

Run `nesk doctor` and `docker version`. Luminesk needs a reachable Docker daemon for
mutable image resolution, builds, and runtime operations. On Linux, confirm the
current user can access the daemon; on macOS and Windows, start Docker Desktop.

## A remote install asks for confirmation

Luminesk prints the source, resolved revision, build-code status, write target, and
download count. Review the recipe, then rerun with `--yes`. Automation must use
both `--non-interactive` and `--yes`; Luminesk will not silently trust a remote
recipe.

## `--frozen` fails

Frozen mode is intentionally strict. Check that:

- `luminesk.toml` still matches the lock's manifest digest;
- the lock target matches the current platform;
- every locked source blob exists in the content cache.

Run `nesk cache verify`. To refresh the lock and cache, run a connected
`nesk lock` or update after reviewing the new resolution.

## Update refuses a managed file

Run `nesk diff --dir INSTANCE`. Luminesk refuses to overwrite a managed/generated
file whose digest no longer matches the ownership ledger. Preserve your edit in
a data path or recipe change, restore the applied file, and preview again.

## Runtime readiness fails

Read `nesk logs --dir INSTANCE`, inspect the recipe checks, image digest, mounts,
ports, and input values. A required readiness failure rolls the runtime back; it
does not commit the failed container as healthy.

## Interrupted transaction

Luminesk normally recovers from its journal on the next operation. For explicit
recovery:

```bash
nesk recover --dir INSTANCE
nesk validate --dir INSTANCE --instance
```

## Rebuild a missing index entry

```bash
nesk import INSTANCE
nesk import /srv/minecraft --scan
```

Only directories with valid local instance state are imported.
