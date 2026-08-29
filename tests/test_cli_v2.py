from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from luminesk_cli.cli.entry import main
from luminesk_cli.infrastructure import recipe as recipe_module
from luminesk_cli.infrastructure.recipe import (
    GitRecipeSource,
    RecipeCheckout,
    checkout_recipe,
)


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
    assert result.stdout == "nesk 2.0.0\n\n"


def test_local_cli_install_emits_json_and_writes_instance(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache-home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config-home"))
    root = tmp_path / "server"
    root.mkdir()
    (root / "server.jar.in").write_bytes(b"server")
    (root / "luminesk.toml").write_text(
        '''\
manifest_version = 1
[package]
name = "cli-fixture"
version = "1.0.0"
[[sources]]
id = "core"
provider = "local-file"
path = "server.jar.in"
target = "server.jar"
[runtime]
driver = "docker"
image = "fixture/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["java", "-jar", "server.jar"]
''',
        encoding="utf-8",
    )

    exit_code = main(["install", "--dir", str(root), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["dryRun"] is False
    assert (root / "server.jar").read_bytes() == b"server"
    assert (root / ".luminesk_cli/state.json").is_file()


def test_keep_git_reports_missing_optional_executable(
    tmp_path: Path, monkeypatch
) -> None:
    source = GitRecipeSource(
        canonical="github:owner/repo",
        clone_url="https://github.com/owner/repo.git",
        owner="owner",
        repository="repo",
        requested_ref=None,
    )
    monkeypatch.setattr(recipe_module.shutil, "which", lambda name: None)

    from luminesk_cli.domain.errors import ResolutionError

    try:
        checkout_recipe(source, tmp_path / "recipe", require_git=True)
    except ResolutionError as exc:
        assert "requires the git executable" in str(exc)
    else:
        raise AssertionError("missing Git was not reported")


def test_normal_checkout_uses_api_path_without_git(
    tmp_path: Path, monkeypatch
) -> None:
    source = GitRecipeSource(
        canonical="github:owner/repo",
        clone_url="https://github.com/owner/repo.git",
        owner="owner",
        repository="repo",
        requested_ref=None,
    )
    expected = RecipeCheckout(
        root=tmp_path / "recipe",
        source=source,
        revision="a" * 40,
        tracking_ref="main",
        tracked_files=("luminesk.toml",),
    )
    monkeypatch.setattr(
        recipe_module,
        "_checkout_github_archive",
        lambda source, destination: expected,
    )
    monkeypatch.setattr(
        recipe_module,
        "_checkout_with_git",
        lambda source, destination: (_ for _ in ()).throw(
            AssertionError("Git path must not be used")
        ),
    )

    assert checkout_recipe(source, tmp_path / "recipe") == expected
