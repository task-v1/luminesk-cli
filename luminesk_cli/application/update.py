"""Runtime-aware update orchestration with readiness rollback."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from luminesk_cli.application.install import (
    TransactionalInstaller,
    prune_instance_backups,
    restore_install_backup,
)
from luminesk_cli.application.runtime import DockerRuntime
from luminesk_cli.domain.errors import TransactionError
from luminesk_cli.domain.instance import InstanceState
from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.manifest import Manifest
from luminesk_cli.domain.package import ServerPackage
from luminesk_cli.domain.plan import Plan
from luminesk_cli.domain.recipe import RecipeSnapshot
from luminesk_cli.infrastructure.state import state_directory


@dataclass(slots=True, frozen=True)
class UpdateResult:
    install_plan: Plan
    state: InstanceState | None
    rolled_back: bool = False


class UpdateService:
    def __init__(
        self,
        *,
        runtime: DockerRuntime | None = None,
        installer: TransactionalInstaller | None = None,
    ) -> None:
        self.runtime = runtime or DockerRuntime()
        self.installer = installer or TransactionalInstaller()

    def update(
        self,
        root: Path,
        manifest: Manifest,
        lockfile: Lockfile,
        package: ServerPackage,
        *,
        inputs: dict[str, str | int | bool],
        recipe_snapshot: RecipeSnapshot,
        dry_run: bool = False,
    ) -> UpdateResult:
        root = root.resolve()
        install_plan = self.installer.plan(package, root)

        if dry_run:
            return UpdateResult(install_plan, None)

        transaction_id = uuid.uuid4().hex
        backup = state_directory(root) / "backups" / transaction_id
        previous_state = self.runtime.status(root)
        was_running = previous_state.runtime.status == "running"

        if was_running:
            self.runtime.stop(root)

        try:
            _, state = self.installer.install(
                manifest,
                lockfile,
                package,
                root,
                inputs=inputs,
                transaction_id=transaction_id,
                prune_backups=False,
                recipe_snapshot=recipe_snapshot,
            )

            if state is None:
                raise TransactionError(
                    "update did not produce committed instance state"
                )

            if was_running:
                state = self.runtime.start(root, wait_for_readiness=True)

            prune_instance_backups(root, manifest.update.retain_backups)
            return UpdateResult(install_plan, state)
        except BaseException as exc:
            try:
                current_state = self.runtime.status(root)

                if current_state.runtime.status == "running":
                    self.runtime.stop(root, remove=True)

                if (backup / "install-plan.json").is_file():
                    restore_install_backup(root, backup)

                if was_running:
                    self.runtime.start(root, wait_for_readiness=True)
            except BaseException as rollback_exc:
                raise TransactionError(
                    "update failed and the previous runtime could not be restored",
                    original=str(exc),
                    rollback=str(rollback_exc),
                    transaction=transaction_id,
                ) from exc

            raise TransactionError(
                "update failed; the previous instance was restored",
                original=str(exc),
                transaction=transaction_id,
            ) from exc
