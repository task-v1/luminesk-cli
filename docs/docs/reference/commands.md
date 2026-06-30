# Commands Cheat Sheet

A quick reference guide for all **Luminesk** CLI commands, syntax structures, and option flags.

---

| Command | Alias | Arguments | Key Options | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`create`** | `new`, `init`| None | `-n`, `-d`, `-c`, `-t`, `-f`, `-m`, `-j` | Creates and registers a new server (starts Wizard if no options given). |
| **`start`** | `s` | `[tag]` | `-l` (loop), `-d` (detached) | Boots a server container and attaches or runs in the background. |
| **`stop`** | `st` | `<tag\|pid>`| `-f` (stops loop mode) | Gracefully shuts down the Minecraft server process. |
| **`kill`** | `k` | `<tag\|pid>`| `-f` (stops loop mode) | Force-terminates the container process immediately. |
| **`attach`** | `a` | `[tag]` | None | Binds your console stdin/stdout to a running background container. |
| **`list`** | `ls`, `l` | None | `-t`, `-s`, `-c` | Prints a status grid of all registered server instances. |
| **`cores`** | `c` | None | None | Lists available Nukkit core engine profiles from registry. |
| **`diagnostic`**| `check`, `diag`| None | None | Verifies connectivity to all online package release hosts. |
| **`upgrade-core`**| `upcore`| `[tag]` | `-r` (redownload) | Compares and downloads engine upgrades from registry sources. |
| **`change-java`**| `java` | `[tag]` | `-j <java>` | Changes the target Java version or JRE container image. |
| **`change-lang`**| `lang` | `[lang]` | None | Toggles display localization (en, ru, uk, ja, zh). |
| **`delete`** | `d` | `<tag>` | `-y` (yes) | Unregisters the server metadata profile from SQLite database and deletes metadata. |
