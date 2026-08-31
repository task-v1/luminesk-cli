from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path

import pytest

from luminesk_cli.application.locking import LockService
from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.domain.lockfile import Lockfile, RuntimeLock
from luminesk_cli.domain.manifest import parse_manifest
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.template import read_template_tree


def _manifest(extra: bytes = b"") -> bytes:
    return (
        b"""\
manifest_version = 1
template = "template"
[package]
name = "template-fixture"
version = "2.0.0"
kind = "template"
game = "minecraft"
edition = "cross-platform"
[inputs.name]
type = "string"
default = "Luminesk Server"
[inputs.eula]
type = "boolean"
default = true
[runtime]
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["./run-helper"]
"""
        + extra
    )


def _lock(manifest_digest: str) -> Lockfile:
    return Lockfile(
        manifest_digest=manifest_digest,
        target="linux/amd64",
        sources={},
        runtime=RuntimeLock(image=f"example/server@sha256:{'a' * 64}"),
    )


def test_template_suffix_interpolation_binary_and_ownership(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe"
    template = recipe / "template"
    (template / "world").mkdir(parents=True)
    (template / "eula.txt.tmpl").write_bytes(b"eula=${input.eula}\n")
    (template / "server.properties.tmpl").write_bytes(
        b"motd=${input.name}\nliteral=${HOME}\n"
    )
    (template / "icon.bin").write_bytes(b"\x00\xff\x01")
    (template / "run-helper").write_bytes(b"helper")
    (template / "world" / ".keep").write_bytes(b"")
    manifest_bytes = _manifest(
        b"""\
[ownership]
preserve = ["server.properties"]
data = ["world"]
executable = ["run-helper"]
"""
    )
    (recipe / "luminesk.toml").write_bytes(manifest_bytes)
    manifest = parse_manifest(manifest_bytes)
    package = DeclarativeBuilder(ContentCache(tmp_path / "cache")).build(
        manifest,
        _lock(manifest.digest),
        recipe,
        tmp_path / "template.lumineskpkg",
    )

    metadata = {item.path: item for item in package.metadata.files}
    assert metadata["eula.txt"].ownership == "generated"
    assert metadata["server.properties"].ownership == "preserve"
    assert metadata["world"].ownership == "data"
    assert metadata["world/.keep"].ownership == "data"
    assert metadata["run-helper"].mode & stat.S_IXUSR
    with zipfile.ZipFile(package.path) as archive:
        assert archive.read("payload/eula.txt") == b"eula=true\n"
        assert archive.read("payload/server.properties") == (
            b"motd=Luminesk Server\nliteral=${HOME}\n"
        )
        assert archive.read("payload/icon.bin") == b"\x00\xff\x01"
        assert "payload/eula.txt.tmpl" not in archive.namelist()


def test_template_digest_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe"
    template = recipe / "template"
    template.mkdir(parents=True)
    path = template / "server.properties.tmpl"
    path.write_text("motd=one\n", encoding="utf-8")
    manifest = parse_manifest(_manifest())

    first = read_template_tree(recipe, manifest)
    second = read_template_tree(recipe, manifest)
    assert first is not None
    assert second is not None
    assert first.digest == second.digest

    path.write_text("motd=two\n", encoding="utf-8")
    changed = read_template_tree(recipe, manifest)
    assert changed is not None
    assert changed.digest != first.digest


def test_template_rejects_missing_input(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe"
    template = recipe / "template"
    template.mkdir(parents=True)
    (template / "config.txt.tmpl").write_text(
        "value=${input.missing}",
        encoding="utf-8",
    )
    manifest = parse_manifest(_manifest())

    with pytest.raises(ValidationError, match="missing input"):
        DeclarativeBuilder(ContentCache(tmp_path / "cache")).build(
            manifest,
            _lock(manifest.digest),
            recipe,
            tmp_path / "missing.lumineskpkg",
        )


def test_template_rejects_symlink_and_hardlink(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe"
    template = recipe / "template"
    template.mkdir(parents=True)
    source = template / "source.txt"
    source.write_text("content", encoding="utf-8")
    symlink = template / "link.txt"
    symlink.symlink_to(source)
    manifest = parse_manifest(_manifest())

    with pytest.raises(SecurityError, match="symlink"):
        read_template_tree(recipe, manifest)

    symlink.unlink()
    os.link(source, template / "hardlink.txt")
    with pytest.raises(SecurityError, match="hardlink"):
        read_template_tree(recipe, manifest)


def test_template_file_count_is_bounded(tmp_path: Path, monkeypatch) -> None:
    from luminesk_cli.infrastructure import template as template_module

    recipe = tmp_path / "recipe"
    template = recipe / "template"
    template.mkdir(parents=True)
    (template / "one").write_bytes(b"1")
    (template / "two").write_bytes(b"2")
    monkeypatch.setattr(template_module, "MAX_TEMPLATE_FILES", 1)

    with pytest.raises(SecurityError, match="too many"):
        read_template_tree(recipe, parse_manifest(_manifest()))


def test_template_collision_with_artifact_is_rejected(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe"
    template = recipe / "template"
    template.mkdir(parents=True)
    (template / "server.jar.tmpl").write_bytes(b"template")
    (recipe / "artifact.jar").write_bytes(b"artifact")
    manifest_bytes = _manifest(
        b"""\
[[sources]]
id = "core"
type = "local-file"
target = "server.jar"
[sources.options]
path = "artifact.jar"
"""
    )
    manifest = parse_manifest(manifest_bytes)
    cache = ContentCache(tmp_path / "cache")
    lockfile = LockService(cache, image_resolver=OciImageResolver()).create(
        manifest,
        recipe,
        target="linux/amd64",
    )

    with pytest.raises(ValidationError, match="collides"):
        DeclarativeBuilder(cache).build(
            manifest,
            lockfile,
            recipe,
            tmp_path / "collision.lumineskpkg",
        )
