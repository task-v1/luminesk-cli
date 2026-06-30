# Docker Integration

Luminesk uses Docker to wrap and isolate Minecraft Bedrock server engines. This page covers how container environments are constructed, named, and mounted.

---

## Volume Mounts

The main path mapping configuration during container boot is:

```text
Host System Path                     Container Virtual Path
/home/user/servers/my-server  ===>   /server
```

### Path Resolution:
- Luminesk expands relative paths and resolves symlinks on the host system to compile the absolute directory path.
- The path is cleaned of backslashes (normalized to `/` to ensure Windows compatibility with Docker Desktop).
- The entire folder is mounted using the `--volume` flag. The Java engine's working directory (`--workdir`) is set to `/server` inside the container.

---

## Container Naming Convention

Containers are named dynamically from your server's database tag:
- **Naming Rule**: Prepend `luminesk-` to the tag.
- **Sanitization**: All non-alphanumeric characters (except hyphens and underscores) are replaced with hyphens. Trailing and leading hyphens/underscores are stripped.
  - Example tag: `My.Server_1!`
  - Sanitized tag: `my-server_1`
  - Container Name: `luminesk-my-server_1`
- **Collision Prevention**: Only one container with this name can exist on the Docker daemon at any time. Running `nesk start` will throw an error if a container with the same name is already running or registered.

---

## Command Redirection (FIFO pipe)

Because standard Docker inputs can get blocked when detached, Luminesk injects a custom entrypoint wrapper:

```bash
set -o pipefail
mkdir -p .luminesk/logs
rm -f /tmp/luminesk-console.pipe
mkfifo /tmp/luminesk-console.pipe
chmod 600 /tmp/luminesk-console.pipe

while true; do
  exec 3<> /tmp/luminesk-console.pipe
  java -jar "$LUMINESK_JAR_NAME" < /tmp/luminesk-console.pipe 2>&1 | tee -a "$LUMINESK_LOG_PATH"
  ...
```

This ensures that the container starts up a stable FIFO input pipe. When commands are sent via `nesk stop` or `nesk command`, they are piped cleanly to Java's stdin, and the outputs are saved to the log folder.
