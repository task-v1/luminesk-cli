---
sidebar_position: 8
---

# Server Lifecycle

Runtime commands operate on an installed instance, not a bare recipe. Pass an
explicit `--dir`, or run the command inside an instance; Luminesk searches the
current directory and its parents for `luminesk.toml`.

## Start and readiness

```bash
nesk start --dir ./instance
```

Before starting, Luminesk verifies instance state, the applied lock, and the
canonical installed recipe snapshot. It removes any stale container with the
instance's deterministic name, then creates a detached Docker container from:

- the exact image digest in `luminesk.lock`;
- the recipe's explicit argv command and working directory;
- memory, user, read-only-root, restart, signal, and timeout policy;
- instance-relative bind mounts and explicit TCP/UDP port mappings.

With no declared mounts, the instance root is mounted read-write at the
runtime workdir. With declared mounts, only those mounts are added.

After Docker starts, all readiness checks run in declaration order. If none are
declared, Luminesk uses a five-second `process-alive` check. A required failure
stops and removes the new container and leaves runtime state stopped. During an
update, the outer update transaction additionally restores and restarts the
previous instance.

Use `--no-wait` only while diagnosing a server whose normal readiness condition
cannot pass:

```bash
nesk start --dir ./instance --no-wait
nesk logs --dir ./instance --follow
```

## Observe

```bash
nesk status --dir ./instance
nesk logs --dir ./instance
nesk logs --dir ./instance --follow
nesk attach --dir ./instance
```

`status` inspects Docker instead of trusting stale state and reconciles the
recorded value to `running` or `stopped`. Non-following `logs` can emit JSON;
`logs --follow` owns the terminal and cannot. `attach` is always interactive
and opens a full-screen console. It loads the latest 200 Docker log lines before
streaming new output, so entering the console does not start with an unexplained
blank screen. Type a server command and press Enter to send it.

The bottom bar keeps the console controls visible:

- `Ctrl+C` gracefully stops the server using its configured stop policy;
- `Ctrl+D` detaches the TUI while leaving the server running;
- `Ctrl+K` immediately kills the server;
- `Ctrl+L` clears the local console view;
- `PageUp` and `PageDown` scroll, and `End` resumes following new output.

Console history and live output retained by the TUI are bounded to 1 MiB. The
TUI requires a real terminal and rejects JSON and non-interactive operation.

Readiness log checks save their latest captured output under the instance's
`.luminesk_cli/` diagnostic state, which helps explain a timeout even after the
failed container has been removed.

## Stop and restart

```bash
nesk stop --dir ./instance
nesk restart --dir ./instance
```

The container was created with `[runtime].stop_signal`; `stop` asks Docker to
wait `[runtime].stop_timeout` seconds. `restart` performs a complete stop and
start, including readiness unless `--no-wait` is set.

## Runtime input overrides

`start` and `restart` accept repeatable `--set` and `--set-file`. They are
combined with the non-secret values saved at install/update time and affect
that container creation only. Type, range, and pattern validation runs before
Docker is called. They do not rewrite the installed package or persist new
state. To render updated files and persist non-secret input values, preview and
apply `nesk update` instead.

## Locate and recover instances

The global index is updated on normal installs but is not authoritative for
runtime commands. Multiple instances may share the same recipe-derived tag;
their instance IDs and paths remain distinct. Rebuild missing entries from
local instance state with:

```bash
nesk list
nesk import ./instance
nesk import /srv/minecraft --scan
```

`list` is a local discovery command: it reports the recorded state and marks
unavailable paths as `missing`, but does not contact Docker or reconcile live
container status.

If an interrupted install/update left an active transaction journal, recover it
explicitly and validate the result:

```bash
nesk recover --dir ./instance
nesk validate --dir ./instance --instance
nesk status --dir ./instance
```

See [Runtime and Docker](/docs/runtime-and-docker) for manifest fields and
[Troubleshooting](/docs/troubleshooting) for common container failures.
