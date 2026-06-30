# Server Metadata

Luminesk maintains detailed metadata for each registered server to manage execution, updates, and environment mappings. This metadata is modeled in the `ManagedServer` class and stored in the database.

---

## Metadata Fields

The following properties are stored for each server:

- **`name`**: A human-readable display name for the server. Proposed during creation and used in listings.
- **`tag`**: A unique, lowercase alphanumeric identifier (e.g. `my-server`). Used as the primary key in the database and as the direct argument in CLI commands.
- **`path`**: The absolute path on the host system to the server files directory.
- **`core_id`**: The identifier of the server engine core (e.g. `nukkit`, `pnx`, `nukkit-mot`, or `lumi`).
- **`core_version`**: The version string of the engine (e.g., `1.21.0-r1`). If the core was set up manually or cannot be resolved, this defaults to `None` (rendered as `unknown`).
- **`jar_name`**: The exact filename of the engine executable JAR (e.g., `nukkit.jar`, `server.jar`).
- **`config_file`**: The filename of the server configuration file (e.g., `server.properties`, `pnx.yml`).
- **`port_way`**: The key path inside the config file used to resolve network ports.
- **`java_image`**: The Docker image used to execute the server container (defaults to `eclipse-temurin:21-jre`).
- **`memory_limit`**: The RAM limit assigned to the container (defaults to `1g`).
- **`created_at`**: A UTC timestamp indicating when the server was registered.

---

## Runtime State Metadata

Additionally, the database tracks transient **Runtime** metadata for active servers:

- **`status`**: Execution status (`running` or `stopped`).
- **`pid`**: The system PID of the container runtime process.
- **`loop_enabled`**: Boolean indicating if the restart loop mode is active.
- **`docker_container_id`**: The unique container SHA ID returned by the Docker engine.
- **`docker_container_name`**: The friendly container name on the Docker daemon (e.g., `Luminesk-my-server`).
- **`docker_memory_limit`**: The active memory limit.
- **`last_started_at`**: Timestamp of the last boot.
- **`last_stopped_at`**: Timestamp of the last shutdown.
- **`last_exit_code`**: The exit code returned by the Java engine during the last shutdown/crash.
