import os
import re

ROOT = "/data/data/com.termux/files/home/cli"

def exclude_dir(d):
    return d in {".venv", ".git", ".ruff_cache", "node_modules", ".docusaurus", "build", "__pycache__", "luminesk_cli.egg-info", "assets", "static"}

def rename_dir():
    old_dir = os.path.join(ROOT, "luminesk")
    new_dir = os.path.join(ROOT, "luminesk_cli")

    if os.path.exists(old_dir):
        os.rename(old_dir, new_dir)
        print(f"Renamed {old_dir} to {new_dir}")

def process_file(path):
    if path.endswith(".svg") or path.endswith(".png") or path.endswith(".ico") or path.endswith(".lock") or path.endswith(".json") or path.endswith(".pyc") or path.endswith(".ttf") or path.endswith(".woff2"):
        return

    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return

    original_content = content

    # 1. Replace "Luminesk CLI" with "Luminesk-CLI"
    content = content.replace("Luminesk CLI", "Luminesk-CLI")

    # 2. Replace remaining "Luminesk" with "Luminesk-CLI"
    # But wait, we shouldn't replace it if it's already "Luminesk-CLI" or in a URL like `luminesk.taskov1ch.xyz`.
    # Let's just use regex
    content = re.sub(r'Luminesk(?!\-CLI|\.taskov1ch|\-cli|/|_)b?', 'Luminesk-CLI', content)

    # Also lowercase "luminesk" where it means the python module name or general reference.
    # We should change `from luminesk import` to `from luminesk_cli import`
    content = re.sub(r'\bluminesk\b(?!\-cli|\.taskov1ch|\.main|/|_)', 'luminesk_cli', content)

    # Special fix for pyproject.toml
    content = content.replace('luminesk.main:main', 'luminesk_cli.main:main')
    content = content.replace('luminesk/__main__.py', 'luminesk_cli/__main__.py')
    content = content.replace('include = ["luminesk*"]', 'include = ["luminesk_cli*"]')

    # 3. Replace "Nukkit-based" and "Nukkit базированных" with "MCBE" / "MCBE"
    content = content.replace("Nukkit-based", "MCBE")
    content = content.replace("Nukkit базированных", "MCBE")

    if content != original_content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {path}")

def main():
    rename_dir()

    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not exclude_dir(d)]
        for file in files:
            if file == "rename.py":
                continue

            path = os.path.join(root, file)
            process_file(path)

if __name__ == "__main__":
    main()

