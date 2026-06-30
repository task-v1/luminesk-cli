# Server Configurations

Minecraft Bedrock server engines utilize different configuration files and keys to store settings. This page outlines the target settings files, keys, and how Luminesk parses them.

---

## Configuration File Mappings

Each engine defines a custom file name and port lookup key in the registry:

| Engine | Config File | Port Key Path | Format |
| :--- | :--- | :--- | :--- |
| **Nukkit** | `server.properties` | `server-port` | Flat Properties |
| **PowerNukkitX** | `pnx.yml` | `settings.port` | YAML |
| **Nukkit-MOT** | `server.properties` | `server-port` | Flat Properties |
| **Lumi** | `settings.yml` | `general.server-port`| YAML |

---

## How Luminesk Parses Configurations

To map ports accurately on Windows and macOS, Luminesk inspects the server directory before spawning the container.

### 1. Flat Properties Files (`.properties`)
Properties files are parsed using a simple line-by-line parser (`parse_properties`):
- Skips empty lines and comment lines (starting with `#` or `!`).
- Splits key-value pairs at `=` or `:`.
- Strips surrounding quotes, comments (with `#`), and trailing spaces.
- Returns the value matching the specified key.

### 2. YAML Files (`.yml` / `.yaml`)
Instead of importing heavy external YAML parsers, Luminesk uses a custom, lightweight, indentation-aware parser (`parse_yaml`):
- Skips empty lines and comment lines starting with `#`.
- Tracks indentation levels to rebuild the hierarchical key path.
- Matches dot-separated paths (e.g., `settings.port` or `general.server-port`).
- Resolves and returns the scalar value.
