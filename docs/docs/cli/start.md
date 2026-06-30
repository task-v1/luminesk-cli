# `start` & `attach` commands

Launches a registered Minecraft Bedrock server inside a Docker container, and manages console attachment.

---

## Syntax

### Start a Server
```bash
nesk start [tag] [options]
```

### Attach to a Running Server
```bash
nesk attach [tag]
```
:::tip
If you omit the `tag` argument, Luminesk will look at your current working directory. If that folder is registered under a server, it will resolve and start/attach to it automatically.
:::

---

## Options for `start`

- `-l`, `--loop`: Auto-restart loop. If the server exits or crashes, the container automatically restarts after 5 seconds.
- `-d`, `--detached`: Background execution. The container launches in the background and control returns immediately to your terminal.

---

## Examples

### Launch server interactively (default)
```bash
nesk start my-server
```

### Launch from inside the server directory
```bash
cd /home/user/servers/my-server
nesk start
```

### Run server in the background
```bash
nesk start my-server --detached
```

### Re-attach to a server running in the background
```bash
nesk attach my-server
```

---

## Typical Errors

### `Server '<tag>' is already running (PID <pid>).`
- **Cause**: The server is already active on your system.
- **Solution**: Check running servers using `nesk list`.

### `Core JAR was not found: '<path>'.`
- **Cause**: The server folder exists, but the jar file specified in the metadata (e.g., `nukkit.jar`) is missing.
- **Solution**: Download the core again using `nesk upgrade-core --redownload` or manually place a jar with the matching filename in the folder.

### `Docker container 'Luminesk-<tag>' is already running.`
- **Cause**: An orphaned Docker container from a previous crash or manual launch is using the name.
- **Solution**: Stop/delete it manually using `docker rm -f Luminesk-<tag>`.
