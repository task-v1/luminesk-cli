from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any


def parse_yaml(content: str, path: str) -> str | None:
    parts = path.split(".")
    lines = content.splitlines()
    stack: list[tuple[int, str]] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        while stack and stack[-1][0] >= indent:
            stack.pop()

        if ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip()

            if "#" in val:
                val = val.split("#")[0].strip()

            val = val.strip("'\"")

            stack.append((indent, key))

            current_path = [k for _, k in stack]

            if current_path == parts:
                return val

    return None


def parse_properties(content: str, key: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        for delimiter in ("=", ":"):
            if delimiter in stripped:
                k, v = stripped.split(delimiter, 1)

                if k.strip() == key:
                    val = v.strip()

                    if "#" in val:
                        val = val.split("#")[0].strip()

                    return val.strip("'\"")

    return None


def parse_toml(content: str, path: str) -> str | None:
    try:
        data = tomllib.loads(content)
        parts = path.split(".")
        current: Any = data
        for part in parts:
            if not isinstance(current, dict):
                return None

            current = current.get(part)
        return str(current) if current is not None else None
    except Exception:
        return None


def parse_json(content: str, path: str) -> str | None:
    try:
        data = json.loads(content)
        parts = path.split(".")
        current: Any = data
        for part in parts:
            if not isinstance(current, dict):
                return None

            current = current.get(part)
        return str(current) if current is not None else None
    except Exception:
        return None


def get_server_port(server_path: Path, config_file: str, port_way: str) -> int:
    config_path = server_path / config_file

    if not config_path.exists():
        return 19132

    try:
        content = config_path.read_text(encoding="utf-8")
        val = None
        if config_file.endswith((".yml", ".yaml")):
            val = parse_yaml(content, port_way)
        elif config_file.endswith((".toml", ".toml")):
            val = parse_toml(content, port_way)
        elif config_file.endswith((".json", ".json")):
            val = parse_json(content, port_way)
        else:
            val = parse_properties(content, port_way)

        if val is not None:
            # If the value contains a colon (like in Dragonfly's ":19132" or "0.0.0.0:19132"), extract the port
            if ":" in val:
                val = val.split(":")[-1]

            return int(val)
    except Exception:
        pass

    return 19132
