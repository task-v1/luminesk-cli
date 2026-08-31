"""Validation helpers shared by manifest, lock and package models."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, NoReturn
from urllib.parse import urlsplit

from luminesk_cli.domain.errors import ValidationError

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
OCI_PINNED_IMAGE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._/:~-]{0,254}@sha256:[0-9a-f]{64}$"
)
PACKAGE_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$")
SEMVER_RE = re.compile(
    r"^(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
PLATFORM_RE = re.compile(r"^[a-z0-9]+/[a-z0-9][a-z0-9_-]*$")
WINDOWS_RESERVED_NAMES = {
    "AUX",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def fail(path: str, message: str, value: Any = None) -> NoReturn:
    details = {"field": path}

    if value is not None:
        details["value"] = value

    raise ValidationError(f"{path}: {message}", **details)


def require_table(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(path, "expected a table")

    return value


def require_array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        fail(path, "expected an array")

    return value


def require_string(value: Any, path: str, *, non_empty: bool = True) -> str:
    if not isinstance(value, str):
        fail(path, "expected a string")

    if non_empty and not value.strip():
        fail(path, "must not be empty")

    return value


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        fail(path, "expected a boolean")

    return value


def require_int(
    value: Any,
    path: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        fail(path, "expected an integer")

    if minimum is not None and value < minimum:
        fail(path, f"must be at least {minimum}")

    if maximum is not None and value > maximum:
        fail(path, f"must be at most {maximum}")

    return value


def optional_string(table: dict[str, Any], key: str, path: str) -> str | None:
    value = table.get(key)

    if value is None:
        return None

    return require_string(value, f"{path}.{key}")


def reject_unknown(table: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(table) - allowed)

    if unknown:
        fail(path, f"unknown key: {unknown[0]}")


def require_keys(table: dict[str, Any], required: set[str], path: str) -> None:
    missing = sorted(required - set(table))

    if missing:
        fail(path, f"missing required key: {missing[0]}")


def safe_relative_path(value: Any, path: str, *, allow_dot: bool = False) -> str:
    text = require_string(value, path)
    posix = PurePosixPath(text)
    windows = PureWindowsPath(text)

    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        fail(path, "control characters are not allowed")

    if allow_dot and text == ".":
        return text

    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        fail(path, "must be a relative path")

    if "\\" in text or posix.as_posix() != text:
        fail(path, "must use canonical POSIX separators")

    if any(part in {"", ".", ".."} for part in posix.parts):
        fail(path, "must be normalized and may not contain '.' or '..'")

    for part in posix.parts:
        stem = part.split(".", 1)[0].upper()

        if stem in WINDOWS_RESERVED_NAMES or part.rstrip(" .") != part:
            fail(path, "is not portable across supported platforms")

    return posix.as_posix()


def sha256_digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def validate_digest(value: Any, path: str) -> str:
    digest = require_string(value, path)

    if not SHA256_RE.fullmatch(digest):
        fail(path, "expected sha256:<64 lowercase hex characters>")

    return digest


def validate_pinned_image(value: Any, path: str) -> str:
    image = require_string(value, path)

    if not OCI_PINNED_IMAGE_RE.fullmatch(image):
        fail(path, "expected an OCI image pinned by a lowercase sha256 digest")

    return image


def validate_https_url(
    value: Any,
    path: str,
    *,
    allow_http: bool = False,
) -> str:
    url = require_string(value, path)

    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        fail(path, "control characters are not allowed")

    parsed = urlsplit(url)
    schemes = {"https"}

    if allow_http:
        schemes.add("http")

    if parsed.scheme not in schemes or not parsed.hostname:
        fail(path, "must be an absolute HTTPS URL")

    if parsed.username is not None or parsed.password is not None:
        fail(path, "credentials are not allowed in URLs")

    try:
        parsed.port
    except ValueError:
        fail(path, "contains an invalid port")

    if parsed.fragment:
        fail(path, "fragments are not allowed in URLs")

    return url


def read_bounded_utf8(path: Path, maximum_size: int) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}", path=str(path)) from exc

    if size > maximum_size:
        raise ValidationError(
            f"{path} exceeds the {maximum_size}-byte limit",
            path=str(path),
            size=size,
        )

    try:
        content = path.read_bytes()
        content.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError(
            f"{path} is not a readable UTF-8 file: {exc}", path=str(path)
        ) from exc

    return content
