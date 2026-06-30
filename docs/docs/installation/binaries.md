# Prebuilt Standalone Binaries

For environments where Python is not installed, or you want a simple download-and-run experience, you can use our standalone prebuilt binaries. These binaries are compiled using **PyInstaller** and bundle the Python runtime and dependencies into a single executable.

---

## Download Links

Download the latest version corresponding to your platform from the [GitHub Releases](https://github.com/task-v1/Luminesk/releases) page:

| Platform | Architecture | Binary Download Link |
| :--- | :--- | :--- |
| **Linux** | x64 / AMD64 | [Luminesk-linux-amd64](https://github.com/task-v1/Luminesk/releases/latest/download/Luminesk-linux-amd64) |
| **Linux** | ARM64 | [Luminesk-linux-arm64](https://github.com/task-v1/Luminesk/releases/latest/download/Luminesk-linux-arm64) |
| **macOS** | Intel / AMD64 | [Luminesk-darwin-amd64](https://github.com/task-v1/Luminesk/releases/latest/download/Luminesk-darwin-amd64) |
| **macOS** | Apple Silicon / ARM64 | [Luminesk-darwin-arm64](https://github.com/task-v1/Luminesk/releases/latest/download/Luminesk-darwin-arm64) |
| **Windows** | x64 / AMD64 | [Luminesk-windows-amd64.exe](https://github.com/task-v1/Luminesk/releases/latest/download/Luminesk-windows-amd64.exe) |
| **Windows** | ARM64 | [Luminesk-windows-arm64.exe](https://github.com/task-v1/Luminesk/releases/latest/download/Luminesk-windows-arm64.exe) |

---

## Setup Instructions

### Linux & macOS

1. Download the binary matching your system.
2. Open a terminal and navigate to the directory where the binary was downloaded.
3. Make the binary executable using `chmod`:
   ```bash
   chmod +x Luminesk-linux-amd64
   ```
4. Rename it to `nesk` and move it to a directory in your `PATH` (such as `/usr/local/bin` or `~/.local/bin`):
   ```bash
   mv Luminesk-linux-amd64 ~/.local/bin/nesk
   ```
5. Verify the installation:
   ```bash
   nesk --version
   ```

### Windows

1. Download the `.exe` file.
2. Rename the downloaded file to `nesk.exe`.
3. Create a folder (for example, `C:\Program Files\Luminesk`) and place the `nesk.exe` file inside.
4. Add this directory to your system's Environment Variables `PATH` list:
   - Search for **"Environment Variables"** in the Windows search bar.
   - Edit the `Path` variable under User or System variables.
   - Click **New** and paste the folder path (e.g. `C:\Program Files\Luminesk`).
5. Open a new Command Prompt or PowerShell and verify:
   ```cmd
   nesk --version
   ```
