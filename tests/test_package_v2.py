from __future__ import annotations

from pathlib import Path

from luminesk_cli.application.locking import LockService
from luminesk_cli.domain.manifest import parse_manifest
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.package import verify_package


def test_declarative_build_creates_verified_deterministic_package(
    tmp_path: Path,
) -> None:
    recipe = tmp_path / "recipe"
    recipe.mkdir()
    (recipe / "fixture.jar").write_bytes(b"server")
    (recipe / "server.properties.in").write_text(
        "server-name=${input.name}\nserver-port=${input.port}\n",
        encoding="utf-8",
    )
    manifest = parse_manifest(
        b'''\
manifest_version = 1
[package]
name = "fixture-server"
version = "1.0.0"
[inputs.name]
type = "string"
default = "Nesk"
[inputs.port]
type = "integer"
default = 19132
[[sources]]
id = "core"
provider = "local-file"
path = "fixture.jar"
target = "server.jar"
[[files]]
source = "server.properties.in"
target = "server.properties"
mode = "generated"
template = true
[[files]]
source = "worlds"
target = "worlds"
mode = "data"
[runtime]
driver = "docker"
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["java", "-jar", "server.jar"]
[[checks]]
id = "core-present"
phase = "post-build"
kind = "file"
path = "server.jar"
'''
    )
    cache = ContentCache(tmp_path / "cache")
    lockfile = LockService(
        cache,
        image_resolver=OciImageResolver(),
    ).create(manifest, recipe, target="linux/amd64")
    builder = DeclarativeBuilder(cache)
    first = builder.build(manifest, lockfile, recipe, tmp_path / "one.neskpkg")
    second = builder.build(manifest, lockfile, recipe, tmp_path / "two.neskpkg")

    assert first.digest == second.digest
    assert verify_package(first.path).metadata.name == "fixture-server"
    file_metadata = {item.path: item for item in first.metadata.files}
    assert file_metadata["server.properties"].ownership == "generated"
    assert file_metadata["worlds"].ownership == "data"


def test_template_rejects_environment_interpolation(tmp_path: Path) -> None:
    recipe = tmp_path / "recipe"
    recipe.mkdir()
    (recipe / "fixture.jar").write_bytes(b"server")
    (recipe / "template.txt").write_text("${HOME}", encoding="utf-8")
    manifest = parse_manifest(
        b'''\
manifest_version = 1
[package]
name = "fixture-server"
version = "1.0.0"
[[sources]]
id = "core"
provider = "local-file"
path = "fixture.jar"
target = "server.jar"
[[files]]
source = "template.txt"
target = "config.txt"
template = true
[runtime]
driver = "docker"
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["./server.jar"]
'''
    )
    cache = ContentCache(tmp_path / "cache")
    lockfile = LockService(cache, image_resolver=OciImageResolver()).create(
        manifest, recipe, target="linux/amd64"
    )
    package = DeclarativeBuilder(cache).build(
        manifest, lockfile, recipe, tmp_path / "package.neskpkg"
    )

    import zipfile

    with zipfile.ZipFile(package.path) as archive:
        assert archive.read("payload/config.txt") == b"${HOME}"
