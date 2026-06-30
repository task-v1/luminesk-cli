# Troubleshooting: Server Startup Failures

If your server fails to launch or crashes immediately after starting, follow this guide to identify and resolve the root cause.

---

## Identifying the Crash Cause

When a server starts and then immediately terminates, first inspect the logs:
1. **Luminesk Logs**: Read the latest execution log in `<server-path>/.luminesk/logs/`.
2. **Docker Logs**: Detach and read the raw container output:
   ```bash
   docker logs luminesk-<tag>
   ```

---

## Common Crash Scenarios

### Scenario A: Out of Memory (OOM) / Exit Code 137
- **Symptom**: The server exits abruptly. Running `nesk list` shows the server stopped, and `docker inspect` reports an exit code of `137`.
- **Cause**: The Java Virtual Machine exceeded the memory limit assigned to the container (the cgroup terminated the process).
- **Solution**: Recreate the server with a higher limit (e.g. `--memory 2g`) or optimize the plugin list.

---

### Scenario B: Port Bind Conflict / Address in Use
- **Symptom**: The logs contain BindException errors:
  ```text
  [CRITICAL] **** FAILED TO BIND TO PORT!
  [CRITICAL] * Probably some other server is running on the same port.
  ```
- **Cause**: Another service or server on your host machine is already listening on the configured Bedrock port (default: `19132`).
- **Solution**:
  - Identify what is using the port:
    - **Linux**: `sudo ss -ulnp | grep 19132`
    - **Windows (CMD)**: `netstat -ano | findstr 19132`
  - Stop the conflicting process, or modify the port in your server's settings file (`server.properties` / `pnx.yml` / `settings.yml`).

---

### Scenario C: ClassNotFoundException / Bad Java Version
- **Symptom**: Logs show class execution errors (e.g. `UnsupportedClassVersionError`).
- **Cause**: You are running a modern engine (like PowerNukkitX) on an old Java version.
- **Solution**: Stop the server and upgrade Java:
  ```bash
  nesk change-java <tag> --java 21
  ```
