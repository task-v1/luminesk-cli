# Installation via PyPI

If you have Python installed on your system, you can download and install **Luminesk** directly from **PyPI** (Python Package Index).

---

## Prerequisites

- **Python**: Version **3.13+** is required.
- **Pip**: The Python package installer.

---

## Recommended: Using `pipx`

For command-line tools like Luminesk, it is highly recommended to use **pipx**. This isolates the installation in a dedicated virtual environment, preventing conflicts with other Python packages installed globally or in your user space.

```bash
pipx install Luminesk
```

This command automatically makes the `nesk` command available in your global `PATH`.

---

## Standard Installation

If you prefer standard Python package managers, choose one of the options below:

### Using `pip`
To install globally or in your active virtual environment:

```bash
pip install Luminesk
```

### Using `uv`
If you use the fast modern Python packager **uv**:

```bash
uv pip install Luminesk
```

---

## Verifying the Installation

Check the installed version by running:

```bash
nesk --version
```
