# Installation from Source

For developers who want to contribute to **Luminesk**, modify the source code, or run the absolute latest development version, you can clone the repository and run the application from source.

---

## Prerequisites

- **Python**: Version **3.13+** installed.
- **Git**: Installed and configured.
- **uv**: Highly recommended for managing the Python environment and dependencies. Installing uv is simple:
  - **Linux & macOS**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

---

## Step-by-Step Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/task-v1/Luminesk
   cd Luminesk
   ```

2. **Initialize a Virtual Environment**:
   Using `uv`, you can create a virtual environment instantly:
   ```bash
   uv venv
   ```

3. **Install Dependencies**:
   Sync and install all necessary dependencies (including development and building dependencies if required):
   ```bash
   uv sync
   ```

4. **Verify the Source Launch**:
   Run the CLI wrapper through your virtual environment:
   ```bash
   uv run nesk --help
   ```

   You will see the help menu containing all the available commands.
