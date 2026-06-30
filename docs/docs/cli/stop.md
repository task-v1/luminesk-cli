# `stop`, `kill` & `delete` commands

Commands to stop, terminate, or remove servers from the registry.

---

## Syntax

### Stop a Server (Graceful)
```bash
nesk stop <tag|pid> [options]
```

### Kill a Server (Immediate)
```bash
nesk kill <tag|pid> [options]
```

### Delete a Server Registry
```bash
nesk delete <tag>
```
:::note
For `stop` and `kill`, you can pass either the server's **tag** (e.g. `my-server`) or its running process **PID** (e.g. `35210`).
:::

---

## Options for `stop` and `kill`

- `-f`, `--force`: Stops loop mode together with the server. If a server is running with `--loop`, a normal stop/kill will just trigger a restart; adding `--force` stops the restart loop entirely.

---

## Examples

### Stop a server gracefully
```bash
nesk stop my-server
```

### Stop a server by PID
```bash
nesk stop 35210
```

### Terminate a server and stop its restart loop
```bash
nesk stop my-server --force
```

### Instantly kill a server container
```bash
nesk kill my-server --force
```

### Delete a server from Luminesk database
```bash
nesk delete my-server
```

---

## Typical Errors

### `Server '<tag>' is not running.`
- **Cause**: You tried to stop or kill a server that is already stopped.
- **Solution**: Check server status with `nesk list`.

### `Server '<tag>' is in loop mode and currently waiting to restart. Use --force to stop it permanently.`
- **Cause**: The server process exited, but loop mode is active, waiting to boot it up again.
- **Solution**: Execute the command with `--force`: `nesk stop <tag> --force`.

### `Server '<tag>' must be stopped before it can be deleted.`
- **Cause**: You ran `delete` on an active/running server.
- **Solution**: Stop it first (`nesk stop <tag>`), then run the delete command.
