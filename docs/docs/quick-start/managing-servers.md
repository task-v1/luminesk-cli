# Managing Servers

This page covers basic operations to control, monitor, and remove servers registered with **Luminesk**.

---

## Stopping a Server

Luminesk offers two levels of termination: graceful stop and force termination.

### 1. Graceful Stop
To stop a server gracefully, use the `stop` command:

```bash
nesk stop my-server
```
Luminesk will write `stop` to the server's input console, allowing the engine to save maps, disconnect players, and shut down cleanly.

#### Handling Restart Loops:
If the server was started in loop mode (`--loop`), running `stop` will trigger a restart since loop mode is designed to keep the server online. To stop both the server and the restart loop permanently, use the `--force` option:

```bash
nesk stop my-server --force
```

### 2. Force Kill
If a server becomes completely unresponsive (e.g., deadlock, infinite loop in a plugin), force-kill the container immediately using:

```bash
nesk kill my-server
```

Similar to `stop`, if the server is in loop mode, you must add `--force` to prevent the loop controller from restarting it:
```bash
nesk kill my-server --force
```

---

## Monitoring and Listing Servers

To get a comprehensive overview of all registered servers, their runtime statuses, active PIDs, Java versions, uptimes, and directories, run:

```bash
nesk list
```

This outputs a detailed status table:
```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         Luminesk Servers                                         │
├───────────┬───────────┬─────────┬─────────┬─────────┬──────┬──────────┬────────────┬─────────────┤
│ Tag       │ Name      │ Core    │ Java    │ Status  │ PID  │ Uptime   │ Last Start │ Last Stop   │
├───────────┼───────────┼─────────┼─────────┼─────────┼──────┼──────────┼────────────┼─────────────┤
│ my-server │ My Server │ nukkit  │ java21  │ running │ 2410 │ 01:23:45 │ 2026-06-10 │ -           │
│ test      │ Test Core │ pnx     │ java21  │ stopped │ -    │ -        │ 2026-06-09 │ 2026-06-09  │
└───────────┴───────────┴─────────┴─────────┴─────────┴──────┴──────────┴────────────┴─────────────┘
```

You can filter the server list using flags:
- Filter by status: `nesk list --status running` (or `stopped`)
- Filter by core engine: `nesk list --core pnx`
- Filter by specific tag: `nesk list --tag my-server`

---

## Deleting a Server from Luminesk

If you want to unregister a server from the Luminesk database so that it no longer appears in `nesk list`, use the `delete` command:

```bash
nesk delete my-server
```
:::warning
The `delete` command **only removes the registry entry** from the Luminesk database. It **does not delete the files** in your server directory. If you want to wipe the files, you must delete the directory manually (e.g. `rm -rf ./servers/my-server`).

You cannot delete a server that is currently running. Stop the server first before executing `delete`.
:::
