from __future__ import annotations

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from luminesk_cli.cli.entry import main
from luminesk_cli.domain.lockfile import Lockfile, RecipeLock, RuntimeLock
from luminesk_cli.domain.manifest import parse_manifest
from luminesk_cli.domain.plan import Plan
from luminesk_cli.domain.preview import Preview
from luminesk_cli.infrastructure.recipe_snapshot import create_recipe_snapshot


def test_human_output_uses_restrained_semantic_colors() -> None:
    from luminesk_cli.cli.output import THEME, human_message

    stream = StringIO()
    console = Console(
        file=stream,
        force_terminal=True,
        color_system="truecolor",
        no_color=False,
        highlight=False,
        theme=THEME,
        width=120,
    )
    message = human_message(
        "Install preview\n"
        "  Runtime image: example/server@sha256:" + "a" * 64 + "\n"
        "  add      server.jar — managed file\n"
        "Warning: review this change",
        tone="info",
    )

    console.print(message)
    rendered = stream.getvalue()

    assert "\x1b[" in rendered
    assert "38;2;122;162;200m" in rendered
    assert "38;2;127;174;131m" in rendered
    assert "38;2;200;169;107m" in rendered
    assert message.plain == (
        "Install preview\n"
        "  Runtime image: example/server@sha256:" + "a" * 64 + "\n"
        "  add      server.jar — managed file\n"
        "Warning: review this change"
    )


def test_human_output_does_not_interpret_markup_or_terminal_controls() -> None:
    from luminesk_cli.cli.output import human_message

    message = human_message("Created [red]server[/red]\x1b[31m")

    assert message.plain == "Created [red]server[/red]�[31m"


def test_version_cold_path_does_not_import_heavy_dependencies() -> None:
    script = (
        "import sys; from luminesk_cli.cli.entry import main; "
        "code=main(['--version']); "
        "print(','.join(n for n in ('httpx','rich','sqlite3','cyclopts') "
        "if n in sys.modules)); raise SystemExit(code)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )

    assert result.returncode == 0
    assert result.stdout == "Luminesk 2.0.0\n\n"


def test_doctor_reports_healthy_cli_and_daemon(monkeypatch, capsys) -> None:
    from luminesk_cli.cli.commands import doctor

    monkeypatch.setattr(doctor.shutil, "which", lambda executable: "/usr/bin/docker")
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, '{"Client":{"Version":"28.0"}}\n', ""
        ),
    )
    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)

    assert [item["component"] for item in payload["checks"]] == ["docker"]
    assert payload["checks"][0]["daemonReachable"] is True


def test_debug_diagnostics_use_stderr_without_changing_json(
    monkeypatch, capsys
) -> None:
    from luminesk_cli.cli.commands import doctor

    monkeypatch.setattr(doctor.shutil, "which", lambda executable: "/usr/bin/docker")
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, '{"Client":{"Version":"27"}}', ""
        ),
    )

    assert main(["doctor", "--debug", "--json"]) == 0
    captured = capsys.readouterr()

    assert json.loads(captured.out)["ok"] is True
    assert "DEBUG luminesk_cli.cli.dispatch: command started name=doctor" in (
        captured.err
    )
    assert "command completed name=doctor exit_code=0" in captured.err

    assert main(["doctor", "--json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is True
    assert captured.err == ""


def test_debug_trace_omits_exception_text(capsys) -> None:
    import logging

    from luminesk_cli.cli.debug import configure_debug, log_exception_frames

    secret = "never-log-this-secret"
    configure_debug(True)
    try:
        try:
            raise RuntimeError(secret)
        except RuntimeError as exc:
            log_exception_frames(logging.getLogger("luminesk_cli.security-test"), exc)
    finally:
        configure_debug(False)

    captured = capsys.readouterr()
    assert "exception_type=RuntimeError" in captured.err
    assert secret not in captured.err


def test_doctor_fails_when_docker_is_unavailable(monkeypatch, capsys) -> None:
    from luminesk_cli.cli.commands import doctor

    monkeypatch.setattr(doctor.shutil, "which", lambda executable: None)

    assert main(["doctor", "--json"]) == 8
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "runtime"
    assert payload["error"]["details"]["checks"][0]["available"] is False


def test_human_errors_are_written_to_stderr(tmp_path: Path, capsys) -> None:
    assert main(["validate", "--dir", str(tmp_path)]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error [validation]" in captured.err


def test_parser_usage_errors_honor_json(capsys) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["search", "--unknown-option", "--json"])

    assert raised.value.code == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert captured.err == ""
    assert payload["error"]["code"] == "usage"
    assert "usage:" in payload["error"]["details"]["usage"]


def test_local_cli_install_emits_json_and_writes_instance(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache-home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config-home"))
    root = tmp_path / "server"
    root.mkdir()
    (root / "server.jar.in").write_bytes(b"server")
    (root / "luminesk.toml").write_text(
        """\
manifest_version = 1
[package]
name = "cli-fixture"
version = "2.0.0"
kind = "core"
game = "minecraft"
edition = "bedrock"
[inputs.memory]
type = "string"
default = "2g"
[inputs.port]
type = "integer"
default = 25565
[inputs.data_dir]
type = "string"
default = "data"
[[sources]]
id = "core"
type = "local-file"
target = "server.jar"
[sources.options]
path = "server.jar.in"
[runtime]
image = "fixture/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["java", "-Xmx${input.memory}", "-jar", "server.jar"]
memory = "${input.memory}"
[[runtime.mounts]]
source = "${input.data_dir}"
target = "/server/${input.data_dir}"
[[runtime.ports]]
name = "game"
host = "${input.port}"
container = "${input.port}"
""",
        encoding="utf-8",
    )

    exit_code = main(["install", "--dir", str(root), "--set", "memory=3g", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["dryRun"] is False
    assert payload["preview"]["trust"]["classification"] == "local"
    assert payload["preview"]["capabilities"]["runtime"]["image"].startswith(
        "fixture/server@sha256:"
    )
    assert payload["preview"]["capabilities"]["runtime"]["command"] == [
        "java",
        "-Xmx3g",
        "-jar",
        "server.jar",
    ]
    assert payload["preview"]["capabilities"]["runtime"]["memory"] == "3g"
    assert payload["preview"]["capabilities"]["runtime"]["mounts"] == [
        {"source": "data", "target": "/server/data", "mode": "rw"}
    ]
    assert payload["preview"]["capabilities"]["runtime"]["ports"] == [
        {
            "name": "game",
            "host": 25565,
            "container": 25565,
            "protocol": "tcp",
        }
    ]
    assert payload["preview"]["plan"]["changes"] == payload["changes"]
    assert (root / "server.jar").read_bytes() == b"server"
    assert (root / ".luminesk_cli/state.json").is_file()
    lock = json.loads((root / "luminesk.lock").read_text(encoding="utf-8"))
    assert lock["recipe"] == {
        "kind": "local",
        "source": "local",
        "revision": lock["manifestDigest"],
        "entry": None,
        "path": None,
        "ref": None,
        "tracking": False,
        "version": "2.0.0",
        "manifestDigest": lock["manifestDigest"],
        "templateDigest": None,
    }

    assert main(["diff", "--dir", str(root), "--json"]) == 0
    diff = json.loads(capsys.readouterr().out)
    assert diff["recipeDrift"] == []
    assert diff["upstreamRecipeDiff"] == []
    assert diff["managedFileDrift"] == []

    assert main(["plan", "--dir", str(root), "--frozen", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    with (root / "luminesk.toml").open("a", encoding="utf-8") as handle:
        handle.write("\n# local drift\n")
    assert main(["start", "--dir", str(root), "--json"]) != 0
    error = json.loads(capsys.readouterr().out)
    assert "differs from the locked recipe snapshot" in error["error"]["message"]


def test_remote_recipe_is_built_and_planned_before_confirmation(
    tmp_path: Path, monkeypatch
) -> None:
    from luminesk_cli.cli.commands import install as install_command

    manifest_bytes = b"""\
manifest_version = 1
[package]
name = "remote-fixture"
version = "2.0.0"
kind = "core"
game = "minecraft"
edition = "bedrock"
[[sources]]
id = "artifact"
type = "local-file"
target = "server.bin"
[sources.options]
path = "artifact.bin"
[runtime]
image = "example/server:2"
command = ["server"]
"""
    manifest = parse_manifest(manifest_bytes)
    lockfile = Lockfile(
        manifest_digest=manifest.digest,
        target="linux/amd64",
        sources={},
        runtime=RuntimeLock(image=f"example/server@sha256:{'a' * 64}"),
        recipe=RecipeLock(
            kind="github",
            source="github:owner/repo",
            revision="b" * 40,
            version="2.0.0",
            manifest_digest=manifest.digest,
            ref="main",
            tracking=True,
        ),
    )
    root = tmp_path / "recipe"
    root.mkdir()
    (root / "luminesk.toml").write_bytes(manifest_bytes)
    (root / "artifact.bin").write_bytes(b"artifact")
    snapshot = create_recipe_snapshot(
        root,
        manifest,
        kind="github",
        source="github:owner/repo",
        revision="b" * 40,
        ref="main",
        tracking=True,
    )
    preview = Preview.for_install(snapshot, lockfile, Plan("install", "target", ()))
    rendered_preview = preview.to_text()
    assert "    . -> /server (rw)" in rendered_preview
    for section in (
        "Trust:",
        "Manifest digest:",
        "Resolved artifacts:",
        "Runtime command:",
        "Mounts:",
        "Ports:",
        "Ownership preserve:",
        "Checks:",
        "Changes (0):",
    ):
        assert section in rendered_preview
    events: list[str] = []
    monkeypatch.setattr(
        install_command,
        "resolve_lock",
        lambda *args, **kwargs: lockfile,
    )
    monkeypatch.setattr(install_command, "parse_inputs", lambda *args: {})
    monkeypatch.setattr(
        install_command,
        "_confirm",
        lambda *args: events.append("confirm"),
    )

    def build(*args):
        events.append("build")
        package = SimpleNamespace(metadata=SimpleNamespace(files=()))
        return SimpleNamespace(cleanup=lambda: None), package

    class FakeInstaller:
        def __init__(self, **kwargs):
            del kwargs

        def plan(self, package, target):
            del package
            events.append("plan")
            return Plan("install", str(target), ())

    monkeypatch.setattr(install_command, "build_package", build)
    monkeypatch.setattr(install_command, "TransactionalInstaller", FakeInstaller)
    namespace = SimpleNamespace(
        frozen=False,
        set=[],
        set_file=[],
        dry_run=True,
        json=False,
        yes=True,
        non_interactive=True,
    )

    assert (
        install_command._install_snapshot(
            namespace,
            snapshot,
            tmp_path / "target",
            confirm=True,
        )
        == 0
    )

    assert events == ["build", "plan", "confirm"]
