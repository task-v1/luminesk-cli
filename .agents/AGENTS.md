# Project Rules & Guidelines

## About the Project
**Luminesk-CLI** is a composer and management CLI tool for Minecraft Bedrock Edition (MCBE) servers.
It is designed to facilitate:
- Local MCBE server development
- Small-scale production deployments
- Convenient management of multiple Minecraft servers using Docker containers

Supported server engines include Nukkit, PowerNukkitX, Nukkit-MOT, Lumi, and others.

---

## Strict rules
* No `pip`, `poetry`, or other commands—exclusively `uv`. Only use other utilities as a fallback if `uv` is unavailable.
  Example:
  ```
  # Wrong!

  uv --version
  # uv 0.11.25

  pip install mypy
  .venv\Scripts\python -m ...
  ```
  ```
  # Right.
  uv add mypy # uv pip install mypy
  uv run ...

  # Output: Error: uv not found!
  pip ...
  ```

* If the package is missing but is required for the work, don't take matters into your own hands; simply state that the agent cannot proceed with the task.

* Follow PEP8 strictly! Additionally, there is an extra rule: leave a blank line before and after `if`, `for`, and other similar statement blocks.
  Example:
  ```
  # Wrong!
  x = 1
  if x == 1:
      print("True")
      while False:
          print("Dont work")
  for i in range(x + 5):
      print(i)
  return x
  ```
  ```
  # Right
  x = 1

  if x == 1:
      print("True")

      while False:
          print("Dont work")

  for i in range(x + 5):
      print(i)

  return x
  ```

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
