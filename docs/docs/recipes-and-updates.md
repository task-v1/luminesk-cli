---
sidebar_position: 6
---

# Recipes and Updates

## Recipe trust model

A recipe is untrusted input. Before install, Luminesk parses a strict schema and
rejects unknown keys, unsafe paths, host commands, dynamic Dockerfile base
images, ambiguous release assets, and unsupported source providers.

Review these fields yourself:

- source repository and requested ref;
- `[permissions]` and `[build.permissions]`;
- Dockerfile contents when a build is declared;
- runtime image, command, mounts, ports, user, and read-only-root setting;
- generated versus preserved/data file ownership;
- post-build and readiness checks.

## Resolution and locking

Providers currently include GitHub Releases, Maven repositories, Jenkins,
direct HTTP, and local files. Resolution downloads each selected artifact into
a content-addressed cache and records its actual size and SHA-256. OCI runtime
and Dockerfile base images are resolved to exact repository digests.

`luminesk.lock` is canonical JSON bound to the digest of `luminesk.toml` and the
target platform. `--frozen` rejects a changed manifest, a different platform,
or a missing cache blob instead of reaching the network.

## Ownership-aware updates

Package entries have one of four ownership modes:

- `managed` — Luminesk may replace it when the applied digest still matches;
- `generated` — rendered from declared inputs and tracked by digest;
- `preserve` — an existing user file wins;
- `data` — user-owned paths such as worlds and plugin data.

An update refuses unsafe overwrites, stages changes, snapshots protected paths,
switches atomically where possible, and commits state only after checks pass.
On failure it restores both recipe files and instance payload.

Use this review loop:

```bash
nesk outdated --dir ./instance
nesk diff --dir ./instance
nesk update --dir ./instance --dry-run
nesk update --dir ./instance --yes
```
