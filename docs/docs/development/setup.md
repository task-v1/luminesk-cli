# Development Setup

This page guides contributors through setting up a local development environment for **Luminesk** using **uv**.

---

## 1. Setting Up the Environment

Luminesk uses **uv** as its primary environment and package manager. 

### Step-by-Step Instructions:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/task-v1/Luminesk
   cd Luminesk
   ```

2. **Install uv** (if you don't have it):
   - **Linux & macOS**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - **Windows**:
     ```powershell
     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```

3. **Synchronize dependencies**:
   Create a virtual environment and sync the packages defined in `pyproject.toml` and `uv.lock`:
   ```bash
   uv venv
   uv sync
   ```

4. **Verify environment execution**:
   Run the CLI wrapper directly inside the virtual environment:
   ```bash
   uv run nesk --help
   ```

---

## 2. Running Automated Tests

Luminesk uses **pytest** for testing. 

### Run all tests:
```bash
uv run pytest
```

### Run tests with coverage reporting:
```bash
uv run pytest --cov=Luminesk
```

Make sure all tests pass successfully before pushing changes or opening a pull request.
