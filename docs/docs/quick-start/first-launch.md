# Launching Your Server

Once you have created your server, you can start running it. Luminesk gives you flexible execution modes: interactive attachment, detached background mode, and restart loop mode.

---

## Method 1: Start and Attach (Interactive Mode)

By default, launching a server starts the container and attaches your current terminal session directly to the server's console input/output:

```bash
nesk start my-server
```
:::tip
If you are currently in the server's directory (e.g. `/home/user/servers/my-server`), you can omit the tag argument. Luminesk will resolve the directory and start the appropriate server:
```bash
nesk start
```
:::

---

## Method 2: Start in the Background (Detached Mode)

If you are running the server on a remote VPS or want to close your terminal without shutting down the server, run it in **detached mode**:

```bash
nesk start my-server --detached
```

The CLI will start the Docker container in the background and output information:
```text
┌─────────────────────────────────────────────────────────────┐
│                   Docker server started                     │
│                                                             │
│  Server:         My Bedrock Server (my-server)              │
│  Container:      Luminesk-my-server                         │
│  Java:           eclipse-temurin:21-jre                     │
│  Memory Limit:   1g                                         │
│  Log:            /home/user/servers/my-server/logs/latest.log│
└─────────────────────────────────────────────────────────────┘
```

### Attaching to a Running Background Server
To view logs or send console commands to a server running in the background, attach to it:

```bash
nesk attach my-server
```

You can also use standard Docker commands:
```bash
docker logs --follow Luminesk-my-server
```

To exit the logs view without stopping the server, press `Ctrl+C`.

---

## Method 3: Enable the Restart Loop

If you want the server to restart automatically in case of crashes, memory exhaustion, or accidental shutdowns, run it in **loop mode**:

```bash
nesk start my-server --loop
```

If the server shuts down or crashes, Luminesk will capture the exit code, wait for 5 seconds (default restart delay), and boot the server up again.

To stop a server running in loop mode, you must pass the `--force` flag. See [Stopping Servers](managing-servers.md) for details.
