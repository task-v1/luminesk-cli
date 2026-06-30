# Environment Variables

Luminesk checks several environment variables to override default settings, handle authentication limits, and coordinate internal container operations.

---

## User Configuration Variables

These variables can be set on your host machine to control how the Luminesk CLI behaves:

### 1. `LUMINESK_REGISTRY_URL`
- **Purpose**: Overrides the default URL used to download the engine cores catalog JSON.
- **Allowed Formats**:
  - HTTP/HTTPS link: `https://example.com/custom-registry.json`
  - Local file path: `/home/user/my-registry.json`
  - URL file protocol: `file:///home/user/my-registry.json`
- **Default**: `https://gist.github.com/Taskov1ch/27b513878dc2a9c0c29f97423a3bc566/raw`

### 2. `GITHUB_TOKEN`
- **Purpose**: Authenticates queries sent to the GitHub API.
- **Why set this**: GitHub rate-limits anonymous API requests to 60 queries per hour. If you create or update many servers using the GitHub Release provider, setting your personal token lifts limits to 5,000 queries per hour.
- **Example**:
  ```bash
  export GITHUB_TOKEN=ghp_yourpersonaltokenhere
  nesk create ...
  ```

---

## Container Internal Variables

These variables are injected automatically by Luminesk into the Docker container environment during `nesk start` and are used by the entrypoint scripts:

- **`LUMINESK_JAR_NAME`**: The name of the server executable JAR (e.g., `nukkit.jar`). Instructs the start script which package to run.
- **`LUMINESK_LOG_PATH`**: The path within the container filesystem where output streams are saved.
- **`LUMINESK_LOOP`**: Set to `1` if loop mode is active. Instructs the shell entrypoint to restart the server when Java exits.
- **`LUMINESK_RESTART_DELAY`**: Number of seconds the entrypoint waits before restarting a crashed server (defaults to `5` seconds).
