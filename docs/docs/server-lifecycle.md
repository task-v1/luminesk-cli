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
and passes terminal signals to Docker.

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
that container creation only. They do not rewrite the installed package or
persist new state. To render updated files and persist non-secret input values,
preview and apply `nesk update` instead.

## Locate and recover instances

The global index is updated on normal installs but is not authoritative for
runtime commands. Rebuild missing entries from local instance state with:

```bash
nesk import ./instance
nesk import /srv/minecraft --scan
```

If an interrupted install/update left a transaction journal or a restorable
backup, recover it explicitly and validate the result:

```bash
nesk recover --dir ./instance
nesk validate --dir ./instance --instance
nesk status --dir ./instance
```

See [Runtime and Docker](/docs/runtime-and-docker) for manifest fields and
[Troubleshooting](/docs/troubleshooting) for common container failures.
