# Logging & Console Redirection

Monitoring server outputs is essential for debugging issues, checking player joins, and auditing plugin errors. This page describes how Luminesk captures and manages server logs.

---

## Log File Locations

For every server execution, Luminesk generates a local, persistent log file inside the server directory:

- **Directory**: `<server-directory>/.luminesk/logs/`
- **Filename Syntax**: `<tag>-YYYYMMDD-HHMMSS.log`
  - Example: `my-server-20260610-193045.log`

---

## How Logging Works

Luminesk configures logging at the container entrypoint level:
1. **Stream Capture**: Standard Output (`stdout`) and Standard Error (`stderr`) channels of the Java Virtual Machine are combined.
2. **Double Redirection (`tee`)**: The combined stream is written directly to the log file on the host filesystem while simultaneously printing to the Docker container console:
   ```bash
   java -jar "$LUMINESK_JAR_NAME" ... 2>&1 | tee -a "$LUMINESK_LOG_PATH"
   ```
3. **Execution Metadata**: Before starting the JVM, the entrypoint logs metadata about the launch, including the timestamp and the exact command executed.

---

## Accessing Logs

You have two primary ways to follow server logs:

### 1. Using `nesk attach` (Interactive Console)
When you run `nesk attach <tag>`, the CLI binds to the Docker container logs.
- **Log Stream**: Displays the logs in your terminal.
- **Interactive Forwarder**: If your terminal supports interactive input (is a TTY), Luminesk spawns a background thread that listens for your keyboard input and writes it directly to the container's console FIFO pipe (`/tmp/luminesk-console.pipe`). This allows you to type commands (like `op player` or `stop`) interactively.
- **Exit**: Press `Ctrl+C` to detach. The server keeps running in the background.

### 2. Using `docker logs` (Read-only Logs)
If you only need to read the log stream without sending commands, run:

```bash
docker logs --follow luminesk-<tag>
```
To exit, press `Ctrl+C`.
