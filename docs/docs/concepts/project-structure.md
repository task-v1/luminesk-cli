# Project Structure & Storage

Luminesk uses standard system paths to store configuration settings, registry caches, and downloaded engine binaries. This page details where these files are located and how they are structured.

---

## 1. User Configuration Directory

Luminesk stores settings and registered server metadata in the platform's user config folder.

- **Linux**: `~/.config/luminesk/`
- **macOS**: `~/Library/Application Support/luminesk/`
- **Windows**: `%APPDATA%\luminesk\`

### Key Files:
- **`state.sqlite3`**: A SQLite 3 database that stores user settings (such as CLI display language) and a table of all registered servers (names, tags, paths, engines, ports, memory limits, and runtime statuses).
- **`config.json`**: The legacy configuration file format. On startup, if Luminesk detects `config.json` but no `state.sqlite3`, it automatically migrates the server registries to SQLite and archives the legacy config.

---

## 2. User Cache Directory

To improve performance and work offline, Luminesk caches registry indices and downloaded JAR engines in the platform's user cache directory.

- **Linux**: `~/.cache/luminesk/`
- **macOS**: `~/Library/Caches/luminesk/`
- **Windows**: `%USERPROFILE%\AppData\Local\luminesk\Cache\`

### Key Files:
- **`core-registry.json`**: A cached copy of the online engines catalog. It has a Time-To-Live (TTL) of 300 seconds (5 minutes). If you run a command within 5 minutes, it reads the cache instead of making a network request.
- **`cores/`**: Contains subdirectories where downloaded server engine JAR files are cached. When you create a server using an engine version you already downloaded previously, Luminesk copies it from the cache instead of downloading it again.

---

## 3. Server Files directory

Each server you create has a dedicated folder (e.g. inside `./servers/my-server/`).

### Contents:
- **`server.jar`** (or engine-specific name): The executable Java file downloaded by Luminesk.
- **`server.properties`** (or `pnx.yml` / `settings.yml`): The server configuration file detailing ports, difficulty, world names, and game modes.
- **`.luminesk/logs/`**: An internal folder created by Luminesk to store container stdout/stderr log channels. The active logs are continuously appended to `.luminesk/logs/latest.log`.
- **`worlds/`, `plugins/`**: Standard directories created by the Minecraft server engine.
