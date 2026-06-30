# CLI Overview

The **Luminesk** command-line interface provides a clean, unified command set to manage server environments.

---

## Command Syntax

```bash
nesk <command> [arguments] [options]
```

To display the global help menu:
```bash
nesk --help
```

To display help for a specific command:
```bash
nesk <command> --help
```

---

## List of Commands

| Command | Aliases | Description | Link |
| :--- | :--- | :--- | :--- |
| **`create`** | `new`, `init` | Create a new Minecraft Bedrock server | [Go to docs](create.md) |
| **`start`** | `s` | Start a server (interactive or background) | [Go to docs](start.md) |
| **`stop`** | `st` | Gracefully stop a running server | [Go to docs](stop.md) |
| **`kill`** | `k` | Force-kill a running server container | [Go to docs](stop.md) |
| **`list`** | `ls`, `l` | Show all registered servers and their status | [Go to docs](list.md) |
| **`cores`** | `c` | List all available engine cores in the registry | [Go to docs](list.md) |
| **`diagnostic`**| `check`, `diag` | Run checks on repositories and sources | [Go to docs](diagnostic.md) |
| **`upgrade-core`**| `upcore` | Update server engine to the latest version | [Go to docs](update.md) |
| **`change-java`**| `java` | Change Java version or Docker image | [Go to docs](change-java.md) |
| **`change-lang`**| `lang` | Change CLI localization language | [Go to docs](change-java.md) |
| **`delete`** | `d` | Remove a server registry entry from database | [Go to docs](stop.md) |

---

## Global Options

- `-h`, `--help`: Show the help message and exit.
- `-v`, `--version`: Show the version banner and exit.
