# Diagnostics & System Checklist

If you are experiencing unexpected behaviors or commands are failing, walk through this systematic diagnostics guide to isolate the issue.

---

## 1. CLI Core Diagnostics

Always start by running the built-in diagnostic tool:

```bash
nesk diagnostic
```

This verifies that:
- Your core repositories are responding.
- The registry metadata can be fetched.

If a repository is highlighted as **FAIL**, verify your system DNS resolution and check if your local network blocks connections to the repository host (e.g., Maven central or build servers).

---

## 2. Docker Health Checklist

If the CLI fails when launching or stopping servers:

1. **Verify Binary**: Ensure the `docker` command is globally available:
   ```bash
   which docker
   ```
2. **Verify Daemon**: Run a test query:
   ```bash
   docker info
   ```
3. **Verify Permissions**: If `docker info` returns permission errors, verify your user belongs to the `docker` security group (on Linux), or run the command under sudo (not recommended).

---

## 3. Port & Firewall Settings

If players cannot connect to the server even though `nesk list` shows it as `running`:

1. **Check Local Bind**: Verify that the host is listening:
   ```bash
   sudo ss -ulpn | grep 19132
   ```
2. **Check Firewall rules**:
   - **Linux (UFW)**: Allow UDP port traffic:
     ```bash
     sudo ufw allow 19132/udp
     ```
   - **Windows Firewall**: Add an inbound rule allowing UDP and TCP traffic for port `19132`.
   - **Cloud Providers (AWS, Oracle, etc.)**: Add ingress rules in your Security Lists.

---

## 4. Resetting Registry Cache

If engine updates fail, or downloads are consistently corrupted, purge the cache directories:

- **Linux / macOS**:
  ```bash
  rm -rf ~/.cache/Luminesk/
  ```
- **Windows**:
  Wipe the folder `%USERPROFILE%\AppData\Local\Luminesk\Cache\`

Luminesk will download fresh copies of the registry index and jar files on the next command.
