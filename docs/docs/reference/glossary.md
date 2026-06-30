# Glossary of Terms

Definitions of common terms used throughout the **Luminesk** documentation and CLI commands.

---

### Core / Engine
The core server executable (a Java archive `.jar`) that runs the Minecraft Bedrock multiplayer logic. Examples include Nukkit, PowerNukkitX, Nukkit-MOT, and Lumi.

### MCBE (Minecraft Bedrock Edition)
The edition of Minecraft built on the Bedrock codebase, running on Windows 10/11, iOS, Android, Xbox, PlayStation, and Nintendo Switch.

### Registry
An online JSON configuration file that catalogs all supported engines, group IDs, artifact IDs, Jenkins paths, and release patterns. Luminesk reads and caches this registry to download and update cores.

### Tag
A unique case-insensitive alphanumeric label (e.g. `lobby-server`) assigned to a server when it is created. You use tags to target servers directly in CLI commands (e.g. `nesk start lobby-server`).

### Detached Mode
A container launch configuration that starts the Minecraft server in the background and releases control of your terminal immediately, allowing the server to run without an active shell attachment.

### Loop Mode
An execution wrapper that monitors the Minecraft server process. If the server crashes or exits, loop mode automatically restarts it after a short delay.

### FIFO Pipe (Named Pipe)
A virtual file inside the container that behaves like a first-in, first-out buffer. Luminesk redirects Java's input stream to read from this pipe, allowing external commands (via `docker exec`) to be injected into the JVM console stdin.

### Maven / Jenkins / GitHub Release
Remote repository systems and continuous integration build systems used to host, compile, and distribute server engine binaries.
