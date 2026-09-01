from __future__ import annotations

import pytest

from luminesk_cli.domain.errors import ValidationError
from luminesk_cli.domain.manifest import MAX_MANIFEST_SIZE, parse_manifest

VALID_MANIFEST = b"""\
manifest_version = 1

[package]
name = "pnx-basic"
version = "2.0.0"
display_name = "PowerNukkitX"
kind = "core"
game = "minecraft"
edition = "bedrock"
summary = "PowerNukkitX server"
keywords = ["minecraft", "bedrock"]
platforms = ["linux/amd64", "linux/arm64"]

[inputs.port]
type = "integer"
default = 19132
min = 1
max = 65535

[[sources]]
id = "core"
type = "github-release"
target = "server.jar"
[sources.options]
repository = "PowerNukkitX/PowerNukkitX"
version = ">=2.0.0,<3.0.0"
asset = "powernukkitx.jar"

[runtime]
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
"""


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
        (b"manifest_version = 1", b"manifest_version = 2", "manifest_version"),
        (b'name = "pnx-basic"', b'name = "PNX Basic"', "package.name"),
        (b'version = "2.0.0"', b'version = "latest"', "package.version"),
        (b'kind = "core"', b'kind = "plugin"', "package.kind"),
        (b'game = "minecraft"', b'game = "other"', "package.game"),
        (b'edition = "bedrock"', b'edition = "mobile"', "package.edition"),
        (b'target = "server.jar"', b'target = "../server.jar"', "target"),
        (
            b'command = ["java", "-jar", "server.jar"]',
            b'command = "java -jar server.jar"',
            "command",
        ),
        (
            b'image = "eclipse-temurin:21-jre"',
            b'image = "x"\nunknown = true',
            "unknown",
        ),
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

    with pytest.raises(ValidationError, match="unknown key"):
        parse_manifest(content)


def test_manifest_rejects_retired_runtime_driver() -> None:
    content = VALID_MANIFEST.replace(b"[runtime]\n", b'[runtime]\ndriver = "docker"\n')

    with pytest.raises(ValidationError, match="driver"):
        parse_manifest(content)


def test_manifest_rejects_secret_defaults_and_runtime_interpolation() -> None:
    secret_input = b"""
[inputs.token]
type = "string"
secret = true
"""
    content = VALID_MANIFEST.replace(b"[[sources]]", secret_input + b"\n[[sources]]")

    with pytest.raises(ValidationError, match="may not declare a default"):
        parse_manifest(
            content.replace(b"secret = true", b'secret = true\ndefault = "leak"')
        )

    with pytest.raises(ValidationError, match="only be used in rendered files"):
        parse_manifest(
            content.replace(
                b'command = ["java", "-jar", "server.jar"]',
                b'command = ["java", "${input.token}"]',
            )
        )


def test_manifest_rejects_unknown_source_option() -> None:
    content = VALID_MANIFEST.replace(
        b'asset = "powernukkitx.jar"',
        b'asset = "powernukkitx.jar"\njob = "not-a-github-option"',
    )

    with pytest.raises(ValidationError, match="unknown key"):
        parse_manifest(content)


def test_manifest_rejects_unknown_source_type() -> None:
    content = VALID_MANIFEST.replace(
        b'type = "github-release"', b'type = "custom-provider"'
    )

    with pytest.raises(ValidationError, match="unsupported source type"):
        parse_manifest(content)


def test_manifest_parses_java_template_and_ownership() -> None:
    content = VALID_MANIFEST.replace(
        b"manifest_version = 1", b'manifest_version = 1\ntemplate = "template"'
    ).replace(b'edition = "bedrock"', b'edition = "java"')
    content += b"""\n[ownership]\npreserve = ["server.properties"]\ndata = ["world"]\nexecutable = ["run-helper"]\n"""

    manifest = parse_manifest(content)

    assert manifest.template == "template"
    assert manifest.package.edition == "java"
    assert manifest.ownership.data == ("world",)


@pytest.mark.parametrize("template", ["../template", "/template", "a/../template"])
def test_manifest_rejects_unsafe_template_path(template: str) -> None:
    content = VALID_MANIFEST.replace(
        b"manifest_version = 1",
        f'manifest_version = 1\ntemplate = "{template}"'.encode(),
    )

    with pytest.raises(ValidationError, match="template"):
        parse_manifest(content)


def test_manifest_rejects_duplicate_ownership_path() -> None:
    content = (
        VALID_MANIFEST + b"""\n[ownership]\npreserve = ["world"]\ndata = ["world"]\n"""
    )

    with pytest.raises(ValidationError, match="policy path"):
        parse_manifest(content)


def test_manifest_size_is_bounded() -> None:
    with pytest.raises(ValidationError, match="exceeds"):
        parse_manifest(b" " * (MAX_MANIFEST_SIZE + 1))
