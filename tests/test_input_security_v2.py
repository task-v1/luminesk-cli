from __future__ import annotations

import stat
from pathlib import Path

import pytest

from luminesk_cli.cli.commands.common import MAX_INPUT_FILE_SIZE, parse_inputs
from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.lockfile import Lockfile, RuntimeLock
from luminesk_cli.domain.manifest import parse_manifest
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import ContentCache

MANIFEST = b"""\
manifest_version = 1
template = "template"
[package]
name = "secret-fixture"
version = "2.0.0"
kind = "template"
game = "minecraft"
edition = "java"
[inputs.name]
type = "string"
default = "server"
[inputs.token]
type = "string"
required = true
secret = true
[runtime]
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["server"]
"""


def test_secret_input_requires_bounded_utf8_file(tmp_path: Path) -> None:
    manifest = parse_manifest(MANIFEST)
    secret = tmp_path / "token"
    secret.write_text("sensitive value\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="must be supplied with --set-file"):
        parse_inputs(manifest, ["token=leaked"])

    assert parse_inputs(manifest, [], [f"token={secret}"]) == {
        "token": "sensitive value"
    }

    secret.write_bytes(b"x" * (MAX_INPUT_FILE_SIZE + 1))
    with pytest.raises(ValidationError, match="exceeds 64 KiB"):
        parse_inputs(manifest, [], [f"token={secret}"])

    secret.write_bytes(b"\xff")
    with pytest.raises(ValidationError, match="must be UTF-8"):
        parse_inputs(manifest, [], [f"token={secret}"])


def test_secret_rendered_template_is_owner_only(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe"
    template = recipe / "template"
    template.mkdir(parents=True)
    (template / "credentials.txt.tmpl").write_text(
        "token=${input.token}\n", encoding="utf-8"
    )
    (template / "public.txt.tmpl").write_text("name=${input.name}\n", encoding="utf-8")
    manifest = parse_manifest(MANIFEST)
    lock = Lockfile(
        manifest_digest=manifest.digest,
        target="linux/amd64",
        sources={},
        runtime=RuntimeLock(image=f"example/server@sha256:{'a' * 64}"),
    )

    package = DeclarativeBuilder(ContentCache(tmp_path / "cache")).build(
        manifest,
        lock,
        recipe,
        tmp_path / "secret.lumineskpkg",
        inputs={"token": "sensitive value"},
    )
    modes = {item.path: item.mode for item in package.metadata.files}

    assert stat.S_IMODE(modes["credentials.txt"]) == 0o600
    assert stat.S_IMODE(modes["public.txt"]) == 0o644
