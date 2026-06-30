---
sidebar_position: 2
---

# One-Line Installer

The recommended method to install **Luminesk** is our official installer script. It automatically detects your operating system and CPU architecture, downloads the correct prebuilt binary, and sets up environment paths.

---

## Linux & macOS

Run the following command in your terminal:

```bash
curl -fsSL https://Luminesk.taskov1ch.xyz/sh | sh
```

### What the Linux/macOS Script Does:
1. Detects your CPU architecture (e.g., `amd64`, `arm64`).
2. Identifies your OS (Linux or Darwin/macOS).
3. Downloads the latest standalone binary from the official releases on GitHub.
4. Places the binary in your local user binaries directory (e.g., `/usr/local/bin` or `~/.local/bin`).
5. Grants execute permissions (`chmod +x`).

---

## Windows (PowerShell)

Open PowerShell as an Administrator and run:

```powershell
iwr -useb https://Luminesk.taskov1ch.xyz/ps1 | iex
```

### What the Windows Script Does:
1. Validates system environment compatibility.
2. Downloads the compiled `Luminesk-windows-amd64.exe` or `Luminesk-windows-arm64.exe`.
3. Creates a folder under your user profile (e.g., `AppData\Local\Luminesk`).
4. Adds the installation directory to your user's system `PATH` so you can call `nesk` from any command prompt.

---

## Verifying the Installation

After running the script, open a new terminal window and type:

```bash
nesk --version
```

If the installation was successful, it will display the installed version banner:
```text
Luminesk v0.16 by Taskov1ch. License: GPL-3.0.
```
