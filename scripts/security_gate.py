"""Cheap deterministic security invariants complementing CodeQL."""

from __future__ import annotations

import ast
from pathlib import Path

RETIRED_DIRECTORIES = {
    "compatibility_recipes",
    "core",
    "cores",
    "migration",
    "models",
    "utils",
}
DOMAIN_FORBIDDEN_IMPORTS = {"filelock", "httpx", "platformdirs", "rich"}


def main() -> int:
    package = Path("luminesk_cli")
    violations = []

    for directory in RETIRED_DIRECTORIES:
        retired = package / directory

        if retired.exists():
            violations.append(f"retired package directory exists: {directory}")

    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node.func)

                if name in {"eval", "exec"}:
                    violations.append(f"{path}:{node.lineno}: forbidden {name}()")

                for keyword in node.keywords:
                    if (
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ):
                        violations.append(
                            f"{path}:{node.lineno}: subprocess shell=True is forbidden"
                        )

            if path.parent.name == "domain" and isinstance(
                node, (ast.Import, ast.ImportFrom)
            ):
                modules = _imported_modules(node)
                forbidden = modules & DOMAIN_FORBIDDEN_IMPORTS

                if forbidden:
                    violations.append(
                        f"{path}:{node.lineno}: domain imports {sorted(forbidden)}"
                    )

    if violations:
        raise SystemExit("\n".join(violations))

    print("Security contract passed.")
    return 0


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return ""


def _imported_modules(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name.split(".", 1)[0] for alias in node.names}

    return {node.module.split(".", 1)[0]} if node.module else set()


if __name__ == "__main__":
    raise SystemExit(main())
