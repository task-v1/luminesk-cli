# Interactive Wizard Setup

Luminesk features an interactive configuration setup wizard designed to guide you step-by-step through the process of creating a new Minecraft Bedrock server.

---

## Triggering the Wizard

To launch the wizard, simply run the creation command without any options or arguments:

```bash
nesk create
```

---

## Setup Steps

The wizard prompts you for five pieces of configuration:

### 1. Select the Core Engine
- **Prompt**: `Enter the core to use for server creation (default: nukkit)`
- **Input**: Enter a valid registered core ID (e.g., `nukkit`, `pnx`, `nukkit-mot`, or `lumi`).
- **Validation**: If you input an invalid core ID, the CLI prints an error panel and lists available cores, asking you to enter it again.

### 2. Enter Server Name
- **Prompt**: `Enter the server name (default: Nukkit Server)`
- **Input**: A user-friendly name for identification. It is purely metadata and does not write to the server's network MOTD.

### 3. Enter Server Tag
- **Prompt**: `Enter the server tag for quick access with nesk start <tag> (default: server-nukkit)`
- **Input**: A short alphanumeric string.
- **Smart Suggestions**: Luminesk checks the database. If `server-nukkit` is already registered, it suggests `server-nukkit-1`, `server-nukkit-2`, etc.
- **Validation**: Verifies the characters match the regex `^[a-zA-Z0-9\-_.]+$`.

### 4. Enter Target Directory
- **Prompt**: `Enter the path to the directory where the server will be created (default: ./servers/server-nukkit)`
- **Input**: The absolute or relative path to store server files.
- **Validation**: Verifies if the path is occupied. If files exist, the wizard will prevent creation to avoid data loss.

### 5. Enter Java Version / Runtime Image
- **Prompt**: `Enter the Java version or Docker image (default: 21)`
- **Input**: E.g. `17`, `21`, or custom image tags.
