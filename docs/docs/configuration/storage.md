# Database Storage Schema

Luminesk uses a local **SQLite 3** database (`state.sqlite3` located inside your user config folder) to persistently store configuration profiles, server metadata, and active container statuses.

---

## Why SQLite?

In earlier versions, Luminesk used a flat `config.json` file. However, writing to JSON files lacks transaction safety, which can lead to data corruption if multiple CLI actions are executed concurrently. 

SQLite provides:
- **ACID Transactions**: Ensures database updates are atomic.
- **Concurrent Access Guarding**: Employs Write-Ahead Logging (WAL) and busy timeout blocks (up to 30 seconds) to prevent locking issues.
- **Auto-Migrations**: Automatically creates or patches schema columns when running new version binaries.

---

## Schema Architecture

The database contains two primary tables:

### 1. `settings` Table
Stores general user preferences.

```sql
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

#### Standard Settings Keys:
- `language`: Selected localization (e.g. `en`, `ru`).
- `default_server_path`: Path prefix proposed for new servers.

### 2. `servers` Table
Stores registered server configurations and runtime status states.

```sql
CREATE TABLE IF NOT EXISTS servers (
    tag TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    core_id TEXT NOT NULL,
    core_version TEXT,
    jar_name TEXT NOT NULL,
    config_file TEXT NOT NULL DEFAULT 'server.properties',
    port_way TEXT NOT NULL DEFAULT 'server-port',
    java_image TEXT NOT NULL DEFAULT 'eclipse-temurin:21-jre',
    memory_limit TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    pid INTEGER,
    loop_enabled INTEGER NOT NULL,
    docker_container_id TEXT,
    docker_container_name TEXT,
    docker_memory_limit TEXT,
    last_started_at TEXT,
    last_stopped_at TEXT,
    last_exit_code INTEGER
);
```

### Indexes:
To speed up server directory lookups when executing `nesk start` from the current directory, a path index is built:
```sql
CREATE INDEX IF NOT EXISTS idx_servers_path ON servers(path);
```
