# `list` & `cores` commands

Commands to view registered servers, monitor their runtime metrics, and check available engine cores.

---

## Syntax

### List Servers
```bash
nesk list [options]
```

### List Core Engines
```bash
nesk cores
```

---

## Options for `list`

- `-t`, `--tag <tag>`: Filters the table output to show only the server with the matching tag.
- `-s`, `--status <running|stopped>`: Filters servers by status.
- `-c`, `--core <id>`: Filters servers using a specific engine ID (e.g. `pnx`).

---

## Output Fields in `list`

When running `nesk list`, a table is printed with the following fields:

- **Tag**: Unique server identifier.
- **Name**: User-friendly display name.
- **Core**: The engine core ID.
- **Java**: Java version or Docker image.
- **Status**: Current execution state (`running` or `stopped`), with indicator tags like `(loop)` or `(docker: container_name)`.
- **PID**: Host system process ID of the Java server.
- **Uptime**: Elapsed running time formatted as `HH:MM:SS`.
- **Last Start**: Date and time of the last server boot.
- **Last Stop**: Date and time of the last shutdown.
- **Path**: Full absolute directory path of the server files.

---

## Examples

### View all servers
```bash
nesk list
```

### Filter to show only running servers
```bash
nesk list --status running
```

### List available server cores in the registry
```bash
nesk cores
```
Output:
```text
Available Cores
* Nukkit
  Original Minecraft server core.
* PowerNukkitX
  Advanced core with support for newer blocks and entities.
...
```
