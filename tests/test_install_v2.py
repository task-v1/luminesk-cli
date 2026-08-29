from __future__ import annotations

from pathlib import Path

import pytest

from luminesk_cli.application.install import TransactionalInstaller
from luminesk_cli.application.locking import LockService
from luminesk_cli.domain.errors import ConflictError, TransactionError
from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.manifest import Manifest, parse_manifest
from luminesk_cli.domain.package import ServerPackage
from luminesk_cli.infrastructure.build import DeclarativeBuilder
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.state import load_ownership, load_state


def make_package(
    tmp_path: Path,
    version: str,
    content: bytes,
) -> tuple[Manifest, Lockfile, ServerPackage]:
    recipe = tmp_path / f"recipe-{version}"
    recipe.mkdir()
    (recipe / "fixture.jar").write_bytes(content)
    manifest = parse_manifest(
        f'''\
manifest_version = 1
[package]
name = "fixture-server"
version = "{version}"
[[sources]]
id = "core"
provider = "local-file"
path = "fixture.jar"
target = "server.jar"
[[files]]
source = "worlds"
target = "worlds"
mode = "data"
[runtime]
driver = "docker"
image = "example/server@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
command = ["java", "-jar", "server.jar"]
[update]
backup = ["worlds"]
retain_backups = 2
'''.encode()
    )
    cache = ContentCache(tmp_path / "cache")
    lockfile = LockService(cache, image_resolver=OciImageResolver()).create(
        manifest, recipe, target="linux/amd64"
    )
    package = DeclarativeBuilder(cache).build(
        manifest,
        lockfile,
        recipe,
        tmp_path / f"fixture-{version}.neskpkg",
    )
    return manifest, lockfile, package


def test_install_is_transactional_and_idempotent(tmp_path: Path) -> None:
    manifest, lockfile, package = make_package(tmp_path, "1.0.0", b"version one")
    target = tmp_path / "instance"
    installer = TransactionalInstaller()

    plan, state = installer.install(manifest, lockfile, package, target)

    assert state is not None
    assert (target / "server.jar").read_bytes() == b"version one"
    assert (target / ".luminesk_cli/state.json").is_file()
    assert (target / ".luminesk_cli/ownership.json").is_file()
    assert not (target / ".luminesk_cli/transaction.json").exists()
    assert any(change.action == "create" for change in plan.changes)

    second_plan, second_state = installer.install(
        manifest, lockfile, package, target
    )

    assert second_state is not None
    assert second_state.instance_id == state.instance_id
    assert all(change.action == "preserve" for change in second_plan.changes)


def test_install_refuses_to_overwrite_user_drift(tmp_path: Path) -> None:
    first_manifest, first_lock, first_package = make_package(
        tmp_path, "1.0.0", b"version one"
    )
    target = tmp_path / "instance"
    installer = TransactionalInstaller()
    installer.install(first_manifest, first_lock, first_package, target)
    (target / "server.jar").write_bytes(b"user modified")
    second_manifest, second_lock, second_package = make_package(
        tmp_path, "2.0.0", b"version two"
    )

    with pytest.raises(ConflictError, match="conflicts"):
        installer.install(
            second_manifest,
            second_lock,
            second_package,
            target,
        )

    assert (target / "server.jar").read_bytes() == b"user modified"
    assert load_state(target).installed_package_digest == first_package.digest  # type: ignore[union-attr]


def test_failed_update_restores_files_and_metadata(tmp_path: Path) -> None:
    first_manifest, first_lock, first_package = make_package(
        tmp_path, "1.0.0", b"version one"
    )
    target = tmp_path / "instance"
    TransactionalInstaller().install(
        first_manifest, first_lock, first_package, target
    )
    old_state = load_state(target)
    old_ownership = load_ownership(target)
    second_manifest, second_lock, second_package = make_package(
        tmp_path, "2.0.0", b"version two"
    )

    def fail_after_first_write(path: str) -> None:
        raise RuntimeError(f"injected failure after {path}")

    installer = TransactionalInstaller(apply_hook=fail_after_first_write)

    with pytest.raises(TransactionError, match="rolled back"):
        installer.install(
            second_manifest,
            second_lock,
            second_package,
            target,
        )

    assert (target / "server.jar").read_bytes() == b"version one"
    assert load_state(target) == old_state
    assert load_ownership(target) == old_ownership
    assert not (target / ".luminesk_cli/transaction.json").exists()


def test_dry_run_does_not_create_target(tmp_path: Path) -> None:
    manifest, lockfile, package = make_package(tmp_path, "1.0.0", b"server")
    target = tmp_path / "missing-instance"

    plan, state = TransactionalInstaller().install(
        manifest,
        lockfile,
        package,
        target,
        dry_run=True,
    )

    assert plan.operation == "install"
    assert state is None
    assert not target.exists()
