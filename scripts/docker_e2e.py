"""Hermetic Java 21 Docker lifecycle used by the release-blocking E2E job."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from luminesk_cli.cli.entry import main
from luminesk_cli.infrastructure.state import load_state

COMPILER_IMAGE = "eclipse-temurin:21-jdk"
RUNTIME_IMAGE = "eclipse-temurin:21-jre"


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )


def _pinned_image(image: str) -> str:
    _run(["docker", "pull", image])
    inspect = _run(
        ["docker", "image", "inspect", image, "--format", "{{json .RepoDigests}}"]
    )
    digests = json.loads(inspect.stdout)
    if not isinstance(digests, list) or not digests:
        raise SystemExit(f"Docker returned no repository digest for {image}")
    return str(digests[0])


def _prepare_java_recipe(root: Path, pinned_image: str) -> None:
    root.mkdir()
    (root / "template").mkdir()
    (root / "Server.java").write_text(
        """\
import java.net.ServerSocket;
import java.net.Socket;

public final class Server {
    public static void main(String[] args) throws Exception {
        try (ServerSocket server = new ServerSocket(25565)) {
            System.out.println("Done (hermetic Java fixture) For help, type help");
            System.out.flush();
            while (true) {
                try (Socket ignored = server.accept()) {
                    // TCP readiness probes are accepted and closed.
                }
            }
        }
    }
}
""",
        encoding="utf-8",
    )
    _run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--mount",
            f"type=bind,src={root.resolve()},dst=/work",
            "--workdir",
            "/work",
            COMPILER_IMAGE,
            "javac",
            "Server.java",
        ]
    )
    (root / "Server.class").replace(root / "Server.class.in")
    (root / "template/eula.txt.tmpl").write_text(
        "eula=${input.eula}\n", encoding="utf-8"
    )
    (root / "template/server.properties.tmpl").write_text(
        "motd=${input.server_name}\nserver-port=25565\n",
        encoding="utf-8",
    )
    (root / "luminesk.toml").write_text(
        f'''\
manifest_version = 1
template = "template"
[package]
name = "java-docker-e2e"
version = "2.0.0"
display_name = "Hermetic Java Docker E2E"
kind = "core"
game = "minecraft"
edition = "java"
summary = "Synthetic Java 21 lifecycle fixture"
keywords = ["synthetic", "java"]
[inputs.server_name]
type = "string"
default = "Luminesk E2E"
[inputs.eula]
type = "boolean"
required = true
[inputs.memory]
type = "string"
default = "256m"
pattern = "^[1-9][0-9]*[mMgG]$"
[[sources]]
id = "fixture"
type = "local-file"
target = "Server.class"
[sources.options]
path = "Server.class.in"
version = "2.0.0"
[runtime]
image = "{pinned_image}"
command = ["java", "-Xms${{input.memory}}", "-Xmx${{input.memory}}", "Server"]
memory = "${{input.memory}}"
run_as = "65534:65534"
read_only_root = true
[[runtime.ports]]
name = "game"
host = 25565
container = 25565
protocol = "tcp"
[[checks]]
id = "ready"
phase = "readiness"
kind = "log-regex"
pattern = "Done .* For help, type"
timeout = 30
[ownership]
preserve = ["server.properties"]
''',
        encoding="utf-8",
    )


def main_entry() -> int:
    _run(["docker", "pull", COMPILER_IMAGE])
    pinned_image = _pinned_image(RUNTIME_IMAGE)

    with tempfile.TemporaryDirectory(prefix="luminesk-java-e2e-") as temporary:
        base = Path(temporary)
        recipe = base / "recipe"
        instance = base / "instance"
        os.environ["XDG_CACHE_HOME"] = str(base / "cache")
        os.environ["XDG_CONFIG_HOME"] = str(base / "config")
        _prepare_java_recipe(recipe, pinned_image)

        commands = (
            [
                "install",
                str(recipe),
                "--dir",
                str(instance),
                "--set",
                "eula=true",
                "--yes",
                "--json",
                "--non-interactive",
            ],
            ["start", "--dir", str(instance), "--json", "--non-interactive"],
            ["status", "--dir", str(instance), "--json", "--non-interactive"],
            ["logs", "--dir", str(instance), "--json", "--non-interactive"],
            ["restart", "--dir", str(instance), "--json", "--non-interactive"],
            [
                "update",
                "--dir",
                str(instance),
                "--yes",
                "--json",
                "--non-interactive",
            ],
            ["stop", "--dir", str(instance), "--json", "--non-interactive"],
        )
        try:
            for arguments in commands:
                if main(arguments) != 0:
                    raise SystemExit(f"Luminesk Java E2E command failed: {arguments}")
        finally:
            state = load_state(instance)
            if state is not None and state.runtime.container_id:
                subprocess.run(
                    ["docker", "rm", "--force", state.runtime.container_id],
                    check=False,
                    capture_output=True,
                    shell=False,
                )

    print("Hermetic Java 21 Docker lifecycle E2E passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())
