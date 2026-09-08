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

If you only want to run a server, you do not need to author a recipe or edit a
lockfile. Use the official catalog:

```bash
nesk catalog update
nesk search --type core
nesk info RECIPE
nesk install RECIPE --dir ./servers/NAME
```

`info` explains the recipe's inputs before installation. Human-mode `install`
then collects missing values in a wizard and shows the complete plan before it
writes the instance. The recipe, package, and lock concepts below explain what
Luminesk verifies on your behalf; they are not extra setup steps for a catalog
install.

## Design guarantees

- Remote artifacts are downloaded with size limits and verified by SHA-256.
- Runtime and Dockerfile images are locked to repository digests.
- ZIP, TAR, package, and recipe paths are checked before extraction or writes.
- Install and update plans distinguish managed, generated, preserved, and data
  files.
- Failed readiness checks during an update trigger restoration and restart of
  the previous instance; rollback failures are reported separately.
- Runtime commands are argument arrays; recipe-controlled shell evaluation is
  not supported.
- Automation receives stable JSON and exit codes.

Choose the path that matches your task:

- first server: [Installation](/docs/installation) →
  [Quick Start](/docs/quick-start);
- normal operation: [Server Lifecycle](/docs/server-lifecycle);
- safe updates: [Updating Instances](/docs/updating-instances);
- a command failed: [Troubleshooting](/docs/troubleshooting);
- recipe authoring: [Creating a Custom Recipe](/docs/creating-a-recipe);
- an existing Luminesk 1.x deployment: the separate
  [side-by-side migration guide](/docs/migrating-to-2.0).
