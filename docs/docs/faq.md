---
sidebar_position: 11
---

# FAQ

## What does Luminesk manage?

Luminesk resolves a reviewed recipe, installs one Docker-backed server instance,
tracks file ownership, records exact source and image digests, and performs
transactional updates. It is not a game-server implementation or a general
container orchestrator.

## What is a recipe?

A recipe is a directory containing `luminesk.toml` plus any templates,
Dockerfile, and local source files it declares. It describes inputs, artifact
sources, installed files, ownership, runtime settings, checks, and update
policy. Start with [Creating a Recipe](./creating-a-recipe.md).

## Can I install a custom server core?

Yes, when a catalog already provides an appropriate recipe or when you write and
review your own recipe. Luminesk does not treat an arbitrary JAR or binary as a
complete server definition: runtime, files, ownership, and checks still need to
be declared.

## Do end users need Git?

No. GitHub recipe installs use API metadata and a bounded, commit-pinned archive.
Recipe authors may use Git for source control, but Luminesk does not execute the
Git client during installation or operation.

## Do I need Docker?

Yes. Docker is the only runtime driver and is also the isolated build boundary
for recipes that declare `[build]`. `nesk doctor` verifies both the Docker
executable and daemon access.

## Does Luminesk support multiple instances?

Yes. Each instance has its own directory, local control state, runtime container,
inputs, and lock. Commands target one instance with `--dir`; the global index is
used for discovery, not as the authoritative instance state.

## Where should worlds and editable configuration live?

In paths the recipe marks `data` or `preserve`. Managed/generated paths belong
to the recipe and cannot be silently overwritten after an operator edits them.
Check the recipe's ownership and backup declarations before deploying it.

## How do I change an input after installation?

Pass `--set NAME=VALUE` or `--set-file NAME=PATH` to a supported install,
update, or start command. Install and update persist non-secret values in
instance state; start overrides affect that start only. Secret values are never
persisted, must use `--set-file`, and are not available to path templates.

## Is an image tag reproducible?

No. Locking resolves a tag to a full repository SHA-256 digest. Installed apply
and runtime operations require that digest, so a later tag move does not silently
change an already locked instance.

## What is the difference between the manifest and the lock?

`luminesk.toml` is the author's intent. `luminesk.lock` records the resolved
recipe revision, target platform, exact artifact digests, and exact Docker image
digest for one resolution. Both are required for reproducible application.

## Should I commit `luminesk.lock`?

Yes for a recipe you maintain: review and commit manifest and lock changes
together. An installed instance also keeps its applied lock locally. Locks are
platform-specific, so test them on the deployment target.

## Can a recipe run host shell commands?

No. Host shell commands are forbidden. Runtime and command readiness checks are
argv arrays executed without a shell inside the container. A recipe with
`[build]` can execute Docker build instructions after the user reviews and
approves that recipe; build-network access is off unless declared.

## Is there a `[permissions]` section?

No. It is not part of manifest version 1 and is rejected as an unknown key.
Build-code consent is based on the presence of `[build]`; network access for that
build is controlled by `[build].network`.

## What does `manifest_version = 1` mean?

It selects the current recipe manifest schema. It is a file-format version, not
the Luminesk product version and not the server-core version.

## What happens to worlds and configuration on update?

Paths marked `data` remain user-owned and are never recipe-written. `preserve`
paths keep existing content. Managed/generated files change only if their
recorded applied digest still matches, and the recipe's `[update].backup` globs
select protected paths copied into transaction backups.

## Can I update only one component?

Use `nesk update SOURCE_ID` when the recipe has multiple sources.
The command still creates and validates a coherent new lock and plan; it does
not bypass ownership, checks, or transaction safety.

## Can I run offline?

Use `--frozen` only after the matching target lock and every locked source blob
are present in the local content cache. Frozen mode performs no resolution and
fails rather than fetching or changing anything. Docker must still be able to
use the locked image locally.

## Can I install a `.lumineskpkg` file?

The package format and verifier exist for deterministic distribution, but the
current public CLI has no `nesk package` command and does not accept an arbitrary
package as an install target. Use a local recipe directory or a reviewed catalog
recipe. See [Lockfiles and Packages](./lockfile-and-packages.md).

## Can I automate Luminesk?

Yes. Use `--json --non-interactive`, inspect the process exit status and the JSON
`error` object, and add `--yes` only after automation has approved remote recipe
trust or another confirmation. Parser/usage errors may be emitted before JSON
dispatch, but they use the same JSON error envelope whenever `--json` is
present. Without `--json`, errors are written to stderr. Usage errors exit with
code 2.

## Does `nesk doctor` prove that Docker is healthy?

It verifies that the CLI exists and that the current user can contact the
daemon. It does not pull an image, test registry access, or run a recipe; use a
recipe resolution/validation phase for those workload-specific boundaries.

## Can I directly open or import a 1.x instance?

No. The current manifest, lock, state, ownership ledger, and transaction layout
form a clean compatibility boundary. Migrate data side by side; `nesk import`
only rebuilds index entries for already valid current instances. Follow
[Migrating from 1.x](./migrating-to-2.0.md).

## Is Luminesk production-ready?

The CLI enforces verified resolution, ownership-aware plans, transactional file
application, lock digests, and Docker lifecycle checks. Production readiness for
a particular server still depends on recipe review, tested backups and recovery,
Docker operations, capacity planning, monitoring, and workload-specific
acceptance. Treat a new or changed recipe like deployment code.
