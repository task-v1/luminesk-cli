# `create` command

Creates and registers a new Minecraft Bedrock server using the chosen engine and configuration.

---

## Syntax

```bash
nesk create [options]
```
:::note
Running `nesk create` without options will start the **Interactive Wizard**. See [Wizard](wizard.md) for more details.
:::

---

## Options

- `-n`, `--name <text>`: The display name of the server (does not affect the server MOTD). If omitted, defaults to `{core_name} Server` (e.g. `Nukkit Server`).
- `-d`, `--dir <path>`: The target directory for the server. If omitted, defaults to `<default_server_path>/<tag>`.
- `-c`, `--core <id>`: The engine core to download and configure (e.g., `nukkit`, `pnx`, `nukkit-mot`, `lumi`).
- `-t`, `--tag <tag>`: A unique tag to identify the server in other CLI commands. Can only contain letters, numbers, hyphens, underscores, and dots.
- `-f`, `--force`: If target directory exists and is not empty, this flag forces its deletion and overwrites it.
- `-m`, `--memory <limit>`: Sets the Docker RAM allocation limit (e.g. `512m`, `1g`, `2g`). Defaults to `1g`.
- `-j`, `--java <version|image>`: Selects Java version (e.g. `17`, `21`) or custom Docker image. Defaults to `21`.

---

## Examples

### Create a default server using the interactive wizard
```bash
nesk create
```

### Create a PowerNukkitX server with a custom tag
```bash
nesk create --core pnx --tag pnx-server
```

### Create a server with 2 GB RAM and Java 17, overwriting files
```bash
nesk create \
  --name "Heavy Server" \
  --dir ./servers/heavy \
  --core nukkit \
  --tag heavy-nukkit \
  --memory 2g \
  --java 17 \
  --force
```

---

## Typical Errors

### `Directory '<path>' is not empty.`
- **Cause**: You specified a folder that already contains files.
- **Solution**: Change the directory with `-d`, or add the `-f` / `--force` flag to wipe and overwrite the folder.

### `Tag '<tag>' is already in use.`
- **Cause**: A server is already registered with this tag in `state.sqlite3`.
- **Solution**: Use a different tag, or delete the old server with `nesk delete <tag>`.

### `Core '<core_id>' was not found in the registry.`
- **Cause**: The core name specified with `-c` does not match any register entry.
- **Solution**: Run `nesk cores` to check all valid core identifiers.
