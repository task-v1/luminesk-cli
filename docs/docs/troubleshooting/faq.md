# FAQ (Frequently Asked Questions)

Here are answers to the most common questions regarding **Luminesk**.

---

### Can I run multiple Minecraft Bedrock servers simultaneously?
**Yes.** You can run as many servers as your host hardware allows.
- Ensure that each server is registered with a unique **tag**.
- Ensure that you configure different network ports in their configurations (e.g. `19132` for the first server, `19133` for the second server) to prevent port conflicts.

---

### Where are my plugins, worlds, and configs stored?
**On your host filesystem.** Luminesk mounts the folder specified during creation (e.g., `./servers/my-server/`) into the Docker container. This means all configuration files, plugins, database entries, and maps are saved directly on your host machine.

---

### How do I install plugins?
1. Stop the server: `nesk stop my-server`.
2. Locate the `plugins/` directory inside your server folder (e.g., `./servers/my-server/plugins/`).
3. Download the plugin `.jar` file and place it in that folder.
4. Restart the server: `nesk start my-server`.

---

### How do I send admin commands (like `op` or `gamemode`) to a running server?
Attach to the server console:
```bash
nesk attach my-server
```
Type your command (e.g., `op Steve`) and press **Enter**. To detach from the console without stopping the server, press `Ctrl+C`.

---

### Why does my server restart automatically when it stops?
The server was started in **loop mode**. To stop a looping server permanently, use the `--force` flag:
```bash
nesk stop my-server --force
```

---

### How do I update Luminesk itself?
- **One-line installer**: Re-run the install script.
- **PyPI**: Run `pip install --upgrade Luminesk` or `pipx upgrade Luminesk`.
- **Prebuilt Binary**: Download the latest executable matching your platform from the Releases page and replace the old binary.
