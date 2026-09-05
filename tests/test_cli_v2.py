from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from luminesk_cli.cli.entry import main
from luminesk_cli.domain.lockfile import Lockfile, RecipeLock, RuntimeLock
from luminesk_cli.domain.manifest import parse_manifest
from luminesk_cli.domain.plan import Plan
from luminesk_cli.infrastructure.recipe_snapshot import create_recipe_snapshot


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


def test_doctor_reports_only_runtime_dependency(capsys) -> None:
    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)

    assert [item["component"] for item in payload["checks"]] == ["docker"]


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
[[sources]]
id = "core"
type = "local-file"
target = "server.jar"
[sources.options]
path = "server.jar.in"
[runtime]
image = "fixture/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["java", "-jar", "server.jar"]
""",
        encoding="utf-8",
    )

    exit_code = main(["install", "--dir", str(root), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["dryRun"] is False
    assert payload["preview"]["trust"]["classification"] == "local"
    assert payload["preview"]["capabilities"]["runtime"]["image"].startswith(
        "fixture/server@sha256:"
    )
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
        return SimpleNamespace(cleanup=lambda: None), object()

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
