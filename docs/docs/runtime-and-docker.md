---
sidebar_position: 9
---

# Runtime and Docker

Docker is the only runtime driver in Nesk 2.0. The lockfile must contain a full
`repository@sha256:...` image reference; a tag alone is never accepted at apply
or start time.

## Container boundary

- The recipe command is passed as an argv array with `shell=False` semantics.
- Mount sources are relative to the instance root; container targets are
  absolute and validated.
- Ports are explicit TCP or UDP mappings.
- A read-only root filesystem is enabled by default.
- Recipes can declare a non-root `run_as` identity, memory limit, restart policy,
  stop signal, and stop timeout.
- Nesk labels containers with the instance identity and reconciles labels before
  trusting a discovered container.

## Dockerfile builds

Builds run only when both `[build]` and `[permissions].build = true` are present.
Every external `FROM` image is parsed before execution, resolved to a repository
digest, recorded in the lock, and substituted into the build context. Dynamic
`FROM $VARIABLE` expressions are rejected.

The build context is bounded, excludes links and special files, and runs with
declared CPU, memory, timeout, and network settings. Build output is copied from
the container rather than executed on the host.

## Readiness checks

Supported checks include process-alive, log pattern, local TCP, and explicit
container command arrays. TCP readiness is restricted to loopback targets.
Required failures trigger rollback.
