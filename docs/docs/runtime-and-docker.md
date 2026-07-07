---
sidebar_position: 9
---

# Runtime & Docker Model

Luminesk runs server processes in Docker containers.

## Default runtime behavior

- default image: `eclipse-temurin:21-jre`;
- default memory limit: `1g`;
- server directory is mounted into container at `/server`.

## Networking model

### Linux

- uses `--network host`.

### macOS and Windows (Docker Desktop)

- publishes detected server port (UDP + TCP) with `--publish`.

## Logs and attach model

- `nesk start` (without `--detached`) starts and attaches to runtime flow.
- `nesk attach` follows logs for a running server.
- You can also follow logs with Docker:

```bash
docker logs --follow luminesk-<tag>
```

## Loop mode

`nesk start --loop` enables automatic restart behavior after server exit.

Use loop mode carefully in production-like environments and confirm your stop/kill automation handles loop controller behavior.

## Image selection and validation

- `create --image` and `change-image --image` validate image syntax and existence.
- version-only values without repository/tag format are rejected.

## Operational constraints

- Docker binary must be available in PATH.
- Server deletion requires stopped state.
- Image change and core upgrade are intended for stopped servers.
- Luminesk is currently beta software; validate changes before critical workloads.
