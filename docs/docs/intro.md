---
sidebar_position: 1
slug: /
---

# Introduction

Luminesk-CLI is a reproducible composer and lifecycle manager for Minecraft
Java and Bedrock servers. Its command is `nesk`. Instead of an opaque install
script, Luminesk starts from a declarative recipe, resolves its mutable inputs,
builds a verified package, installs it transactionally, and runs the resulting
server in Docker.

The main concepts are:

- **Recipe** — a directory whose `luminesk.toml` describes package metadata,
  artifact sources, files and templates, inputs, ownership, Docker runtime,
  health checks, and update policy. A core recipe installs a runnable server;
  a template recipe is the same public package kind for reusable compositions.
- **Instance** — one installed server directory. It contains the files used by
  the server plus the manifest, lockfile, and `.luminesk_cli/` state needed to
  operate and update it safely.
- **Package** — a deterministic `.lumineskpkg` archive built from one recipe and
  one lock. It is the verified transaction boundary applied to an instance.
- **Lockfile** — `luminesk.lock`, canonical JSON that binds the manifest to a
  platform, exact source hashes and URLs, an OCI image digest, and the exact
  recipe revision when applicable.
- **Docker runtime** — the locked image, explicit argv command, mounts, ports,
  resource policy, and readiness checks used by `nesk start`.

This separation makes installation and update reproducible: mutable provider
metadata is resolved while creating a lock, artifacts are cached and verified
by SHA-256, and later application is tied to the same manifest, lock, package,
and target platform.

## Design guarantees

- Remote artifacts are downloaded with size limits and verified by SHA-256.
- Runtime and Dockerfile images are locked to repository digests.
- ZIP, TAR, package, and recipe paths are checked before extraction or writes.
- Install and update plans distinguish managed, generated, preserved, and data
  files.
- Failed readiness checks restore the previous known-good instance during an
  update.
- Runtime commands are argument arrays; recipe-controlled shell evaluation is
  not supported.
- Automation receives stable JSON and exit codes.

Start with [Installation](/docs/installation), then follow the
[Quick Start](/docs/quick-start). Recipe authors can continue with
[Manifest and Lockfile](/docs/manifest-and-lockfile). Operators upgrading an
old installation should use the separate
[migration guide from Luminesk 1.x](/docs/migrating-to-2.0).
