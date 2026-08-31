from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from luminesk_cli.application.install import TransactionalInstaller
from luminesk_cli.application.locking import LockService
from luminesk_cli.application.update import UpdateService
from luminesk_cli.cli.commands.update import _security_changes
from luminesk_cli.domain.errors import RuntimeOperationError, TransactionError
from luminesk_cli.domain.instance import RuntimeState
from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.manifest import Manifest, parse_manifest
from luminesk_cli.domain.package import ServerPackage
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.recipe_snapshot import create_recipe_snapshot
from luminesk_cli.infrastructure.state import load_state, write_state


def make_release(
    tmp_path: Path,
    version: str,
    artifact: bytes,
) -> tuple[Path, Manifest, Lockfile, ServerPackage]:
    recipe = tmp_path / f"recipe-{version}"
    recipe.mkdir()
    (recipe / "artifact.bin").write_bytes(artifact)
    manifest_bytes = f'''\
manifest_version = 1
[package]
name = "update-fixture"
version = "{version}"
kind = "core"
game = "minecraft"
edition = "bedrock"
[[sources]]
id = "core"
type = "local-file"
target = "server.bin"
[sources.options]
path = "artifact.bin"
[runtime]
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["./server.bin"]
'''.encode()
    (recipe / "luminesk.toml").write_bytes(manifest_bytes)
    manifest = parse_manifest(manifest_bytes)
    cache = ContentCache(tmp_path / "cache")
    snapshot = create_recipe_snapshot(recipe, manifest)
    lockfile = LockService(cache, image_resolver=OciImageResolver()).create(
        manifest,
        recipe,
        recipe_origin=snapshot.origin,
        target="linux/amd64",
    )
    package = DeclarativeBuilder(cache).build(
        manifest,
        lockfile,
        recipe,
        tmp_path / f"update-{version}.lumineskpkg",
    )
    return recipe, manifest, lockfile, package


class FailingThenRecoveringRuntime:
    def __init__(self, failed_package_digest: str) -> None:
        self.failed_package_digest = failed_package_digest
        self.failure_seen = False

    def status(self, root: Path):
        state = load_state(root)
        assert state is not None
        return state

    def stop(self, root: Path, *, remove: bool = False):
        del remove
        state = load_state(root)
        assert state is not None
        stopped = replace(
            state,
            runtime=RuntimeState(driver="docker", status="stopped"),
        )
        write_state(root, stopped)
        return stopped

    def start(self, root: Path, *, wait_for_readiness: bool = True):
        del wait_for_readiness
        state = load_state(root)
        assert state is not None

        if state.installed_package_digest == self.failed_package_digest:
            self.failure_seen = True
            raise RuntimeOperationError("injected readiness failure")

        running = replace(
            state,
            runtime=RuntimeState(
                driver="docker",
                container_id="restored-container",
                status="running",
            ),
        )
        write_state(root, running)
        return running


def test_failed_readiness_restores_previous_running_instance(tmp_path: Path) -> None:
    old_recipe, old_manifest, old_lock, old_package = make_release(
        tmp_path, "2.0.0", b"working"
    )
    target = tmp_path / "instance"
    target.mkdir()
    (target / "luminesk.toml").write_bytes((old_recipe / "luminesk.toml").read_bytes())
    _, old_state = TransactionalInstaller().install(
        old_manifest,
        old_lock,
        old_package,
        target,
        recipe_snapshot=create_recipe_snapshot(old_recipe, old_manifest),
    )
    assert old_state is not None
    old_state = replace(
        old_state,
        runtime=RuntimeState(
            driver="docker",
            container_id="old-container",
            status="running",
        ),
    )
    write_state(target, old_state)
    _, new_manifest, new_lock, new_package = make_release(tmp_path, "2.1.0", b"broken")
    runtime = FailingThenRecoveringRuntime(new_package.digest)
    service = UpdateService(runtime=runtime)  # type: ignore[arg-type]
    new_snapshot = create_recipe_snapshot(
        tmp_path / "recipe-2.1.0",
        new_manifest,
    )

    with pytest.raises(TransactionError, match="previous instance was restored"):
        service.update(
            target,
            new_manifest,
            new_lock,
            new_package,
            inputs={},
            recipe_snapshot=new_snapshot,
        )

    restored = load_state(target)
    assert runtime.failure_seen
    assert restored is not None
    assert restored.installed_package_digest == old_package.digest
    assert restored.runtime.status == "running"
    assert (target / "server.bin").read_bytes() == b"working"
    assert (target / "luminesk.lock").read_bytes() == old_lock.to_bytes()
    assert (target / "luminesk.toml").read_bytes() == (
        old_recipe / "luminesk.toml"
    ).read_bytes()
    assert (target / ".luminesk_cli/recipe/artifact.bin").read_bytes() == b"working"


def test_security_sensitive_endpoint_changes_are_explicit() -> None:
    def manifest(version: str, repository: str, image: str) -> Manifest:
        return parse_manifest(
            f'''\
manifest_version = 1
[package]
name = "endpoint-fixture"
version = "{version}"
kind = "core"
game = "minecraft"
edition = "java"
[[sources]]
id = "core"
type = "maven"
target = "server.jar"
[sources.options]
repository = "{repository}"
group = "example"
artifact = "server"
version = "latest"
[runtime]
image = "{image}"
command = ["java", "-jar", "server.jar"]
'''.encode()
        )

    changes = _security_changes(
        manifest("1.0.0", "https://old.example/releases", "old/server:1"),
        manifest("1.0.1", "https://new.example/releases", "new/server:1"),
    )

    assert changes == [
        {
            "field": "sources.core.repository",
            "from": "https://old.example/releases",
            "to": "https://new.example/releases",
        },
        {
            "field": "runtime.imageRepository",
            "from": "old/server",
            "to": "new/server",
        },
    ]
