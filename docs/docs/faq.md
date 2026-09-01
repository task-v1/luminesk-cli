---
sidebar_position: 11
---

# FAQ

## Do end users need Git?

No. Normal GitHub installs use API metadata and a bounded commit-pinned archive.
Recipe development may use Git as a source-control tool, but the CLI never
executes it during installation or operation.

## Do I need Docker?

Yes. Docker is the runtime driver and also provides the isolated build boundary
for recipes that declare builds.

## Is an image tag reproducible?

No. Luminesk resolves tags during locking and records a full repository SHA-256
digest. Apply and runtime operations reject malformed or tag-only lock entries.

## Can a recipe run host shell commands?

No. Host commands are forbidden. Runtime and readiness commands are explicit
argument arrays executed without a shell. Optional build code runs in a bounded
Docker build after an explicit permission declaration.

## What happens to worlds and configuration on update?

Recipe ownership modes and `[update].backup` decide this. Preserved and data
paths remain user-owned. Managed files are changed only when their applied
digest still matches. Protected paths are backed up before commit.

## Can I automate Luminesk?

Yes. Use `--json --non-interactive`, inspect the stable exit code and error
object, and add `--yes` only after your automation has approved the plan.

## Is Luminesk production-ready?

Luminesk 2.0 has release gates for its transactions, verification boundaries,
platform bundles, and Docker lifecycle. Recipe quality, Docker availability,
tested backups, and workload-specific acceptance remain the operator's
responsibility.
