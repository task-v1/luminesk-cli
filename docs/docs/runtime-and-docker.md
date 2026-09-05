---
sidebar_position: 9
---

# Runtime and Docker

Docker is Luminesk's only runtime driver. The recipe describes a portable
container intent; `luminesk.lock` binds its image to an immutable repository
digest, and lifecycle commands translate the manifest into argument-only Docker
commands.

## Image resolution

```toml
[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-jar", "server.jar", "nogui"]
```

The manifest may use an image tag or a valid
`repository@sha256:<64-lowercase-hex>` reference. During connected locking,
Luminesk inspects the local image, pulls it if no repository digest is present,
and records a full digest reference. Apply and start use only the lock's image;
a tag-only lock entry is invalid.

Image resolution therefore needs both the Docker CLI and a reachable daemon.
`nesk doctor` checks the first; `docker version` checks the second.

## Command and working directory

```toml
[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-Xmx4g", "-jar", "server.jar", "nogui"]
workdir = "/server"
```

`command` is a non-empty argv array appended after the image. Luminesk does not
insert `sh -c`, so `"server.jar; rm -rf /"` would be one literal argument, not
two commands. Environment-variable interpolation and shell expansion are not
performed. Only declared `${input.NAME}` placeholders are substituted.

`workdir` defaults to `/server` and is passed to Docker. Use an absolute path
that exists in the image or under a declared mount.

## Writable data and mounts

```toml
[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-jar", "server.jar", "nogui"]
workdir = "/server"
read_only_root = true

[[runtime.mounts]]
source = "."
target = "/server"
mode = "rw"
```

`read_only_root` defaults to `true`. Writable server state must therefore live
under a read-write bind mount.

Mount `source` is a portable path resolved inside the instance root; escape via
`..`, an absolute path, or a symlinked resolution is rejected. A non-dot source
is created as a directory before Docker starts. `target` is passed to Docker as
the bind destination; use an absolute container path. `mode` is `rw` by default
or `ro` for a read-only bind.

When no mounts are declared, Luminesk implicitly mounts the entire instance
root at `workdir` read-write. As soon as one mount is declared, that implicit
mount disappears; list every path the container needs.

Use [Ownership and User Data](/docs/ownership) to keep `world/`, `plugins/`,
and mutable configuration safe across package updates. Docker mount mode and
Luminesk file ownership solve different problems.

## Ports

Java servers normally publish TCP; Bedrock servers normally publish UDP:

```toml
[[runtime.ports]]
name = "java-game"
host = 25565
container = 25565
protocol = "tcp"

[[runtime.ports]]
name = "bedrock-game"
host = 19132
container = 19132
protocol = "udp"
```

Host and container values must resolve to 1–65535. They may be integers or a
whole input reference such as `${input.port}`. Protocol defaults to `tcp` and
may be `tcp` or `udp`.

The schema has no host-IP field: Luminesk passes `HOST:CONTAINER/PROTOCOL` to
Docker. Control external exposure with Docker/host firewall configuration and
verify it explicitly; do not assume a published management port is local-only.

## User and resources

```toml
[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-jar", "server.jar", "nogui"]
memory = "4g"
run_as = "1000:1000"
```

`memory` is optional. After input interpolation it must be a positive integer
with optional `b`, `k`, `m`, or `g` suffix and is passed as Docker's memory
limit. Coordinate it with a JVM heap setting so the process has room for
non-heap memory.

`run_as` is passed to Docker's `--user`. The recipe/operator must ensure that
the identity can read managed content and write mounted data. Files created by
a container without `run_as` may be owned by root on the host.

Manifest schema v1 has no runtime CPU field. `[build].cpu` limits recipe builds,
not the server container. Apply external Docker controls if a production host
needs CPU policy beyond the public runtime schema.

## Restart and shutdown

```toml
[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-jar", "server.jar", "nogui"]
restart = "unless-stopped"
restart_limit = 0
stop_signal = "SIGINT"
stop_timeout = 30
```

Restart values are `no` (default), `on-failure`, `always`, and
`unless-stopped`. A positive `restart_limit` is appended only to
`on-failure`. `stop_signal` defaults to `SIGINT`; Docker receives it as the
container stop signal. `nesk stop` waits `stop_timeout` seconds (default 30,
minimum 1).

Choose the graceful signal expected by the server implementation and test both
normal stop and update restart. A Docker restart policy is not a substitute for
Luminesk readiness or transactional rollback.

## Lifecycle

```bash
nesk start --dir ./instance
nesk status --dir ./instance
nesk logs --dir ./instance
nesk logs --dir ./instance --follow
nesk restart --dir ./instance
nesk stop --dir ./instance
```

`start` verifies installed state/recipe/lock, removes a stale same-name
container, starts the locked image, and waits for checks. `status` reconciles
state with Docker. `restart` performs stop then start. `attach` attaches an
interactive terminal; it does not support JSON/non-interactive operation.

A start readiness failure stops and removes the new container. An update of a
previously running instance adds a larger safety envelope: it stops the old
container, installs the candidate, starts/checks it, and restores/restarts the
previous package on failure.

See [Checks and Readiness](/docs/checks) for every check kind and phase.

## Dockerfile builds

Some recipes declare an isolated package build:

```toml
[build]
file = ".luminesk/Dockerfile"
output = "/out"
timeout = 1200
cpu = 2
memory = "2g"
network = false
```

There is no `[permissions]` or `[build.permissions]` table. The presence of
`[build]` opts into Dockerfile execution. `network = false` is the default and
uses `--network none`; setting it to `true` gives the build Docker's default
network and expands trust.

Every external `FROM` image is parsed before build, resolved to a repository
digest, stored under `lock.build.images`, and substituted into a temporary
Dockerfile. Dynamic base expressions are rejected. Syntax frontends, if used,
must already be digest-pinned.

The context is bounded, excludes repository/runtime state directories, rejects
links and special files, and receives declared timeout/CPU/memory/network
limits. Luminesk creates a container from the build image and copies only
`build.output` into package staging. It never runs a recipe command directly on
the host.
