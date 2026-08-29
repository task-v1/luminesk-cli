from __future__ import annotations

import pytest

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.manifest import MAX_MANIFEST_SIZE, parse_manifest

VALID_MANIFEST = b'''\
manifest_version = 1

[package]
name = "pnx-basic"
version = "1.0.0"
platforms = ["linux/amd64", "linux/arm64"]

[inputs.port]
type = "integer"
default = 19132
min = 1
max = 65535

[[sources]]
id = "core"
provider = "github-release"
repository = "PowerNukkitX/PowerNukkitX"
version = ">=2.0.0,<3.0.0"
asset = "powernukkitx.jar"
target = "server.jar"

[runtime]
driver = "docker"
image = "eclipse-temurin:21-jre"
command = ["java", "-jar", "server.jar"]

[[runtime.mounts]]
source = "."
target = "/server"

[[runtime.ports]]
name = "bedrock"
host = "${input.port}"
container = "${input.port}"
protocol = "udp"
'''


def test_parse_valid_manifest() -> None:
    manifest = parse_manifest(VALID_MANIFEST)

    assert manifest.package.name == "pnx-basic"
    assert manifest.sources[0].target == "server.jar"
    assert manifest.runtime.command == ("java", "-jar", "server.jar")
    assert manifest.runtime.ports[0].protocol == "udp"
    assert manifest.digest.startswith("sha256:")


@pytest.mark.parametrize(
    ("old", "new", "field"),
    [
        (b'manifest_version = 1', b'manifest_version = 2', "manifest_version"),
        (b'name = "pnx-basic"', b'name = "PNX Basic"', "package.name"),
        (b'version = "1.0.0"', b'version = "latest"', "package.version"),
        (b'target = "server.jar"', b'target = "../server.jar"', "target"),
        (b'command = ["java", "-jar", "server.jar"]', b'command = "java -jar server.jar"', "command"),
        (b'image = "eclipse-temurin:21-jre"', b'image = "x"\nunknown = true', "unknown"),
    ],
)
def test_manifest_rejects_invalid_schema(old: bytes, new: bytes, field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        parse_manifest(VALID_MANIFEST.replace(old, new))


@pytest.mark.parametrize(
    "target",
    [
        "/server.jar",
        "../server.jar",
        "plugins/../../escape.jar",
        "C:\\server.jar",
        "\\\\host\\share\\server.jar",
    ],
)
def test_manifest_rejects_unsafe_target_paths(target: str) -> None:
    content = VALID_MANIFEST.replace(
        b'target = "server.jar"', f"target = '{target}'".encode()
    )

    with pytest.raises(ValidationError, match="target"):
        parse_manifest(content)


def test_manifest_rejects_host_commands() -> None:
    content = VALID_MANIFEST + b"\n[permissions]\nhost_commands = true\n"

    with pytest.raises(ValidationError, match="host commands are forbidden"):
        parse_manifest(content)


def test_manifest_size_is_bounded() -> None:
    with pytest.raises(ValidationError, match="exceeds"):
        parse_manifest(b" " * (MAX_MANIFEST_SIZE + 1))
