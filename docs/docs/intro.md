---
sidebar_position: 1
slug: /
---

# Luminesk-CLI 2.0

Luminesk composes Minecraft server instances from declarative recipes. A
recipe declares sources, generated and preserved files, a Docker runtime,
readiness checks, and update policy. Luminesk resolves mutable inputs into an
immutable lockfile, builds a verified package, and applies changes through a
transaction.

Luminesk 2.0 is a clean format boundary. It accepts only the current
`luminesk.toml`, `luminesk.lock`, `.lumineskpkg`, and instance-state contracts and
does not convert earlier installations.

## Design guarantees

- Remote artifacts are downloaded with size limits and verified by SHA-256.
- Runtime and Dockerfile images are locked to repository digests.
- ZIP, TAR, package, and recipe paths are checked before extraction or writes.
- Install and update plans distinguish managed, generated, preserved, and data
  files.
- Failed readiness checks restore the previous known-good instance.
- Runtime commands are argument arrays; recipe-controlled shell evaluation is
  not supported.
- Automation receives stable JSON and exit codes.

Start with [Installation](/docs/installation), then follow the
[Quick Start](/docs/quick-start). Recipe authors should read
[Manifest and Lockfile](/docs/manifest-and-lockfile) and
[Recipes and Updates](/docs/recipes-and-updates).
