# Troubleshooting: Docker Not Found

Luminesk runs all Minecraft Bedrock servers within Docker containers. If the Docker executable is missing or unavailable, the CLI will display an error.

---

## The Error Message

```text
Error: Docker was not found in PATH.
```

---

## Troubleshooting Steps

### Step 1: Check If Docker Is Installed
Open a new terminal window and type:

```bash
docker --version
```

- **If Docker is not installed**, follow the installation guide below.
- **If Docker is installed**, your shell path might not include the directory where the Docker binary is stored. See Step 3.

### Step 2: Install Docker

Select the command or installer matching your operating system:

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
```
Ensure your user belongs to the `docker` group to run commands without `sudo`:
```bash
sudo usermod -aG docker $USER
```
*(Log out and log back in for changes to take effect).*

#### macOS
- **Recommended**: Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
- **Homebrew**:
  ```bash
  brew install --cask docker
  ```

#### Windows
- Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
- Ensure the WSL 2 backend (Windows Subsystem for Linux) is enabled for optimal performance.

---

### Step 3: Verify the Docker Daemon is Active

Even if Docker is installed, the engine daemon might not be running. Check container status:

```bash
docker ps
```

- **Linux**: Start the service if stopped:
  ```bash
  sudo systemctl start docker
  ```
- **Windows / macOS**: Open the Docker Desktop dashboard and wait for the indicator icon in the bottom corner to turn green.
