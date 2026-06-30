# Container Networking

Minecraft Bedrock Edition uses UDP as its primary transport protocol for client-server gameplay, although some engines and plugins also listen on TCP. Luminesk handles networking differently depending on the host operating system.

---

## 1. Linux Hosts (Host Network Mode)

On Linux machines, Luminesk launches containers using native host networking:

```bash
docker run --network host ...
```

### Key Behaviors:
- **No Virtual Bridge**: The container does not get its own private IP address. Instead, the Java server binds directly to the network interfaces of your host machine.
- **Performance**: Provides the lowest possible latency and overhead.
- **Port Resolution**: The server will listen on whatever port is configured in its settings file (e.g. `19132` in `server.properties` or `pnx.yml`).

---

## 2. Non-Linux Hosts: Windows & macOS (Bridge Port Publishing)

On Windows and macOS, Docker runs inside a virtual machine (Utility VM / Hyper-V or WSL 2 backend). Host networking (`--network host`) is not fully supported or does not expose ports to the outside system.

To solve this, Luminesk uses port publishing:

```bash
docker run --publish <port>:<port>/udp --publish <port>:<port>/tcp ...
```

### Key Behaviors:
- **Automatic Inspection**: Before booting the container, Luminesk reads the server's configuration file (e.g. `server.properties`, `pnx.yml`, or `settings.yml` depending on the core engine).
- **Key Resolution**: It parses the file to locate the network port key (e.g. `settings.port` for PNX, `server-port` for Nukkit).
- **Default Port**: If the configuration file does not exist, it defaults to the standard Bedrock port: **`19132`**.
- **Dual Bindings**: Publishes the port for both **UDP** (primary game traffic) and **TCP** (Query/RCON protocols).
