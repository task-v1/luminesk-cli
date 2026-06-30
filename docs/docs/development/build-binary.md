# Building a Standalone Binary

Luminesk uses **PyInstaller** to bundle Python, dependency libraries (like `cyclopts`, `httpx`, `rich`, `platformdirs`), and the source code into a single, platform-native executable that can run on host systems without requiring Python.

---

## Prerequisites

Install the building dependencies:

```bash
uv sync --extra build
# or install PyInstaller globally
pip install pyinstaller
```

---

## Compilation Commands

### Linux & macOS

Run the compilation script in your shell:

```bash
pyinstaller --onefile --name=Luminesk Luminesk/__main__.py
```

- **Output**: The compiled binary will be placed at `dist/Luminesk`.

### Windows

Run the compilation command in Command Prompt or PowerShell:

```cmd
pyinstaller --onefile --name=Luminesk Luminesk/__main__.py
```

- **Output**: The compiled binary will be placed at `dist\Luminesk.exe`.

---

## How it works

When compiling with the `--onefile` option:
1. **Packaging**: PyInstaller collects the byte-compiled Python modules and dynamic libraries, packaging them into a single executable.
2. **Extraction at Runtime**: When a user executes the binary, it unpacks the runtime to a temporary directory (`_MEIPASS`) and runs the script from there.
3. **Speed**: The build process creates a standalone binary, but decompression can cause a slight delay on the very first execution.
