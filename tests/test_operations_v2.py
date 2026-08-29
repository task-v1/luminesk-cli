from __future__ import annotations

import os
import subprocess
from pathlib import Path

from luminesk_cli.application.runtime import DockerRuntime
from luminesk_cli.domain.instance import InstanceState, RecipeState, RuntimeState
from luminesk_cli.domain.lockfile import Lockfile, RuntimeLock, write_lockfile
from luminesk_cli.domain.manifest import load_manifest
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.state import InstanceIndex, write_state


def test_cache_prune_respects_age_and_dry_run(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_bytes(b"blob")
    cache = ContentCache(tmp_path / "cache")
    from luminesk_cli.infrastructure.cache import digest_file

    digest, _ = digest_file(source)
    blob = cache.store(source, digest)
    os.utime(blob.path, (100, 100))

    assert cache.prune(max_age_seconds=1, dry_run=True, now=200) == (1, 4)
    assert blob.path.is_file()
    assert cache.prune(max_age_seconds=1, now=200) == (1, 4)
    assert not blob.path.exists()


def test_instance_index_list_handles_an_existing_v1_database(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite3"
    path.touch()

    assert InstanceIndex(path).list() == ()


def test_live_readiness_check_updates_state(tmp_path: Path) -> None:
    root = tmp_path / "instance"
    root.mkdir()
    (root / "luminesk.toml").write_text(
        '''\
manifest_version = 1
[package]
name = "readiness-fixture"
version = "1.0.0"
[[sources]]
id = "core"
provider = "local-file"
path = "server.jar"
target = "server.jar"
[runtime]
driver = "docker"
image = "example/server:latest"
command = ["server"]
[[checks]]
id = "ready"
phase = "readiness"
kind = "log-regex"
pattern = "Done"
timeout = 1
''',
        encoding="utf-8",
    )
    manifest = load_manifest(root / "luminesk.toml")
    lockfile = Lockfile(
        manifest_digest=manifest.digest,
        target="linux/amd64",
        sources={},
        runtime=RuntimeLock(image=f"example/server@sha256:{'a' * 64}"),
    )
    write_lockfile(root / "luminesk.lock", lockfile)
    write_state(
        root,
        InstanceState(
            instance_id="12345678-1234-1234-1234-123456789abc",
            name="readiness-fixture",
            tag="readiness-fixture",
            root=str(root),
            applied_lock_digest=lockfile.digest,
            installed_package_digest=f"sha256:{'b' * 64}",
            recipe=RecipeState(),
            inputs={},
            runtime=RuntimeState(container_id="container-id", status="running"),
            created_at="2026-08-29T00:00:00+00:00",
            updated_at="2026-08-29T00:00:00+00:00",
        ),
    )

    def runner(argv, **kwargs):
        output = "true\n" if argv[1] == "inspect" else "Done loading\n"
        return subprocess.CompletedProcess(argv, 0, output, "")

    checked = DockerRuntime(runner=runner).check_readiness(root)

    assert checked.last_readiness_at is not None
