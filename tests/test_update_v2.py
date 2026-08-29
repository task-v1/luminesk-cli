from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from luminesk_cli.application.install import TransactionalInstaller
from luminesk_cli.application.locking import LockService
from luminesk_cli.application.recipe_update import (
    RecipeUpdater,
    record_recipe_ownership,
    restore_recipe_backup,
)
from luminesk_cli.application.update import UpdateService
from luminesk_cli.domain.errors import RuntimeOperationError, TransactionError
from luminesk_cli.domain.instance import RuntimeState
from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.manifest import Manifest, parse_manifest
from luminesk_cli.domain.package import ServerPackage
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.recipe import (
    GitRecipeSource,
    RecipeCheckout,
)
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
[[sources]]
id = "core"
provider = "local-file"
path = "artifact.bin"
target = "server.bin"
[runtime]
driver = "docker"
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["./server.bin"]
'''.encode()
    (recipe / "luminesk.toml").write_bytes(manifest_bytes)
    manifest = parse_manifest(manifest_bytes)
    cache = ContentCache(tmp_path / "cache")
    lockfile = LockService(cache, image_resolver=OciImageResolver()).create(
        manifest, recipe, target="linux/amd64"
    )
    package = DeclarativeBuilder(cache).build(
        manifest,
        lockfile,
        recipe,
        tmp_path / f"update-{version}.neskpkg",
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
        tmp_path, "1.0.0", b"working"
    )
    target = tmp_path / "instance"
    target.mkdir()
    (target / "luminesk.toml").write_bytes(
        (old_recipe / "luminesk.toml").read_bytes()
    )
    _, old_state = TransactionalInstaller().install(
        old_manifest,
        old_lock,
        old_package,
        target,
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
    _, new_manifest, new_lock, new_package = make_release(
        tmp_path, "2.0.0", b"broken"
    )
    runtime = FailingThenRecoveringRuntime(new_package.digest)
    service = UpdateService(runtime=runtime)  # type: ignore[arg-type]

    with pytest.raises(TransactionError, match="previous instance was restored"):
        service.update(
            target,
            new_manifest,
            new_lock,
            new_package,
            inputs={},
        )

    restored = load_state(target)
    assert runtime.failure_seen
    assert restored is not None
    assert restored.installed_package_digest == old_package.digest
    assert restored.runtime.status == "running"
    assert (target / "server.bin").read_bytes() == b"working"


def test_recipe_tree_can_be_restored_from_update_backup(tmp_path: Path) -> None:
    source = GitRecipeSource(
        canonical="github:owner/repo",
        clone_url="https://github.com/owner/repo.git",
        owner="owner",
        repository="repo",
        requested_ref=None,
    )
    old_root = tmp_path / "old-recipe"
    old_root.mkdir()
    (old_root / "luminesk.toml").write_text("old", encoding="utf-8")
    old_checkout = RecipeCheckout(
        old_root,
        source,
        "a" * 40,
        "main",
        ("luminesk.toml",),
    )
    target = tmp_path / "instance"
    target.mkdir()
    (target / "luminesk.toml").write_text("old", encoding="utf-8")
    record_recipe_ownership(old_checkout, target)
    new_root = tmp_path / "new-recipe"
    new_root.mkdir()
    (new_root / "luminesk.toml").write_text("new", encoding="utf-8")
    new_checkout = RecipeCheckout(
        new_root,
        source,
        "b" * 40,
        "main",
        ("luminesk.toml",),
    )
    backup = target / ".luminesk_cli" / "backups" / "transaction"

    RecipeUpdater().apply(new_checkout, target, backup)
    assert (target / "luminesk.toml").read_text(encoding="utf-8") == "new"

    restore_recipe_backup(target, backup)
    assert (target / "luminesk.toml").read_text(encoding="utf-8") == "old"
