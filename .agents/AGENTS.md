# Project Rules & Guidelines

## About the Project
**Luminesk** is a composer and management CLI tool for Minecraft Bedrock Edition (MCBE) servers.
It is designed to facilitate:
- Local MCBE server development
- Small-scale production deployments
- Convenient management of multiple Minecraft servers using Docker containers

Supported server engines include Nukkit, PowerNukkitX, Nukkit-MOT, Lumi, and others.

---

## Code Style & Development Commands

After making any changes to the source code (adding, modifying, or deleting files), you **MUST** run the code formatter and static checks.

### 1. Code Formatting & Linting
Run the project's formatting script (which checks blank lines and executes `ruff check --fix` under the hood):

- **Windows (Command Prompt / PowerShell)**:
  ```bash
  uv run python -X utf8 scripts/format.py --fix
  ```
  *(Using the `-X utf8` flag prevents Python encoding errors when reading UTF-8 files on Windows).*

- **Linux / macOS**:
  ```bash
  uv run python scripts/format.py --fix
  ```

### 2. Static Type Checking
Run type checking across the entire project repository:
```bash
uv run mypy .
```

### 3. Running Automated Tests
Run the test suite to ensure no regressions were introduced:
```bash
uv run pytest
```

Always review the outputs of these commands and resolve any errors or warnings before concluding your task.
