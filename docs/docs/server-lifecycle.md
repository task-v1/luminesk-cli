---
sidebar_position: 8
---

# Server Lifecycle

## Start and readiness

```bash
nesk start --dir ./instance
```

Nesk creates a Docker container from the locked image and the recipe's explicit
argv, mounts, ports, limits, user, restart policy, stop signal, and stop timeout.
It then evaluates required readiness checks. A failed check stops/removes the
new container, restores the previous runtime state, and returns a runtime error.

`--no-wait` skips readiness and should be reserved for diagnosis.

## Observe

```bash
nesk status --dir ./instance
nesk logs --dir ./instance
nesk logs --dir ./instance --follow
nesk attach --dir ./instance
```

`status` inspects Docker rather than trusting stale state. `attach` requires an
interactive terminal. `logs --follow` cannot be combined with `--json`.

## Stop and restart

```bash
nesk stop --dir ./instance
nesk restart --dir ./instance
```

Stop uses the declared signal and timeout. Restart performs the complete stop,
start, and readiness sequence.

## Locate and recover instances

Runtime commands search the current directory and its parents for
`luminesk.toml` when `--dir` is omitted. The global index can be rebuilt without
guessing state:

```bash
nesk import /srv/minecraft --scan
nesk recover --dir ./instance
```
