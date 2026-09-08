---
sidebar_position: 6
---

# Checks and Readiness

Checks verify package output, the installed filesystem, or a running Docker
container. They run in manifest order and have three phases:

| Phase | When it runs | Supported kind | Required failure |
| --- | --- | --- | --- |
| `post-build` | After build, sources, templates, files, and ownership are assembled; before `.lumineskpkg` is written. | `file` | Package build fails; no instance transaction has begun. |
| `post-install` | After plan changes and recipe snapshot are applied; before lock/ownership/state commit. | `file` | Install/update transaction restores previous files and metadata. |
| `readiness` | After a container starts. During update this occurs only if the previous instance was running and is restarted. | `process-alive`, `log-regex`, `tcp`, `command` | New container is stopped/removed. An update also attempts to restore/restart the previous instance. |

If a recipe declares no readiness checks, Luminesk supplies a five-second
required `process-alive` check.

## Common fields

```toml
[[checks]]
id = "ready"
phase = "readiness"
kind = "log-regex"
pattern = "Done"
timeout = 120
required = true
```

- `id` is a unique non-empty label used in errors and diagnostic filenames.
- `phase` and `kind` must be a supported combination.
- `required` defaults to `true`.
- `timeout` defaults to 30 seconds and must be at least 1. It is the polling
  deadline for readiness; file checks are immediate.
- Kind-specific `path`, `pattern`, `host`, `port`, and `command` fields are
  otherwise optional in schema, but a useful check must supply the fields
  documented below.

An optional readiness check (`required = false`) continues after its timeout.
A stopped container is always a runtime failure, including while an optional
check is being polled.

## File checks

```toml
[[checks]]
id = "core-built"
phase = "post-build"
kind = "file"
path = "server.jar"

[[checks]]
id = "config-installed"
phase = "post-install"
kind = "file"
path = "server.properties"
```

`path` is required and is a portable package/instance-relative path. The check
passes only for a regular non-symlink file. It does not inspect contents. File
checks are not allowed in readiness.

Use post-build for an artifact or Dockerfile output and post-install for a
rendered/transactional destination whose presence matters before commit.

## Process-alive checks

```toml
[[checks]]
id = "container-running"
phase = "readiness"
kind = "process-alive"
timeout = 10
```

The check succeeds on the first poll where Docker says the container is
running. It does not prove that Minecraft has opened a port or completed world
loading, so prefer a log, TCP, or command condition for real readiness.

## Log-regex checks

```toml
[[checks]]
id = "minecraft-ready"
phase = "readiness"
kind = "log-regex"
pattern = "Done .* For help, type"
timeout = 120
```

Luminesk repeatedly reads accumulated Docker logs and applies Python regular
expression search. Choose a stable, implementation-specific startup line and
allow enough time for first world generation. On success or timeout, the most
recent captured log tail (up to 1 MiB) is stored at:

```text
.luminesk_cli/logs/readiness-CHECK_ID-YYYYMMDD-HHMMSS.log
```

Avoid secrets in log patterns. Secret inputs are forbidden in all check
fields.

## TCP checks

```toml
[[checks]]
id = "java-port"
phase = "readiness"
kind = "tcp"
host = "127.0.0.1"
port = "${input.port}"
timeout = 60
```

The connection originates on the host running `nesk`, so use the published
host port, not an unexposed container-only port. `host` defaults to
`127.0.0.1` and must resolve syntactically to `localhost` or a loopback IP;
remote/private probing is rejected. `port` accepts 1–65535 or a whole input
reference that resolves into that range.

A successful TCP handshake shows that something accepted a connection. It
does not perform a Minecraft protocol exchange.

## Command checks

```toml
[[checks]]
id = "server-health"
phase = "readiness"
kind = "command"
command = ["test", "-f", "/server/healthy"]
timeout = 60
```

Luminesk runs `docker exec CONTAINER` followed by the declared argv. Exit code
zero succeeds; other codes are retried until timeout. No shell is inserted, so
pipes, redirection, `&&`, and variable expansion do not work unless an explicit
shell executable is itself part of the argv. Keep health commands simple and
available in the locked image.

## A Minecraft readiness policy

For a Paper-like Java server, combine an immediate package invariant with a
server-specific startup log:

```toml
[[checks]]
id = "server-jar-present"
phase = "post-build"
kind = "file"
path = "server.jar"

[[checks]]
id = "paper-ready"
phase = "readiness"
kind = "log-regex"
pattern = "Done .* For help, type"
timeout = 180
required = true
```

For a Bedrock UDP server, a TCP probe is not equivalent to UDP readiness.
Prefer a verified log line or a container command that reflects the specific
server implementation.

## Failure and rollback sequence

For a normal `nesk start`:

```text
create container → mark running → checks fail → stop/remove → mark stopped
```

For `nesk update` when the old instance was running:

```text
stop old → apply candidate → start candidate → checks fail
    → stop candidate → restore transaction backup → start/check old
```

If restoring or restarting the old runtime also fails, Luminesk reports that
rollback was incomplete and keeps the transaction/backup evidence for manual
recovery. Inspect `nesk logs`, readiness log captures, `nesk diff`, and
`.luminesk_cli/backups/` before using `nesk recover`.

An update of an already stopped instance does not start it solely to run
readiness; use `nesk start` or `nesk validate --readiness` afterward when that
is part of your acceptance workflow.
