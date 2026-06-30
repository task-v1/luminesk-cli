# Exit Codes Reference

This page documents the exit codes returned by the **Luminesk** CLI program and its underlying container processes.

---

## CLI Program Exit Codes

The `nesk` command exits with one of the following codes:

- **`0` (Success)**:
  The requested command executed and completed without error.
- **`1` (General Error)**:
  Luminesk encountered a configuration validation error, database lock timeout, failed to fetch remote registry versions, or one of the repository checks failed during `nesk diagnostic`.
- **`130` (Keyboard Interrupt)**:
  The user manually terminated the execution (e.g., pressed `Ctrl+C` while attached to a server console or waiting for downloads).

---

## Container Process Exit Codes

When running a server in attached mode (`nesk start` without `--detached`), the CLI captures the container's exit code and returns it as the final exit status of the `nesk` command:

- **`0`**: The server was shut down cleanly (e.g. typed `stop` in the console).
- **`137` (OOM Killer)**:
  The container was terminated by the host kernel because it exceeded the assigned memory limit (Docker `--memory` constraint).
- **`143` (SIGTERM)**:
  The container was stopped gracefully from the outside (e.g. via `nesk stop` or `docker stop`).
- **`1` (Java crash)**:
  The Java Virtual Machine crashed due to internal engine bugs, bad configuration options, or broken plugins. Check the logs for details.
