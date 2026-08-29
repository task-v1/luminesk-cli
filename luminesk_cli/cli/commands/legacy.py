"""Small 1.x compatibility bridge without the retired Cyclopts dependency."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from luminesk_cli.cli.commands.common import emit
from luminesk_cli.domain.errors import RuntimeOperationError, ValidationError


def run_runtime(command: str, target: str) -> int:
    from luminesk_cli.core.config import UserConfig
    from luminesk_cli.core.manager import (
        ServerManagerError,
        attach_server,
        resolve_server,
        run_server,
        stop_server,
    )

    config = UserConfig.load()

    try:
        server = resolve_server(config, tag=target, directory=Path.cwd())

        if command == "start":
            return run_server(config, server, console=None)

        if command == "attach":
            return attach_server(config, server)

        stop_server(config, tag=target)
        return 0
    except ServerManagerError as exc:
        raise RuntimeOperationError(str(exc)) from exc


def change_image(namespace: Any) -> int:
    from luminesk_cli.core.config import UserConfig
    from luminesk_cli.core.manager import (
        ServerManagerError,
        change_server_image,
        resolve_server,
    )

    if namespace.image is None:
        raise ValidationError("deprecated change-image requires --image")

    config = UserConfig.load()

    try:
        server = resolve_server(config, tag=namespace.target, directory=Path.cwd())
        updated = change_server_image(config, server, namespace.image)
    except ServerManagerError as exc:
        raise RuntimeOperationError(str(exc)) from exc

    emit(
        namespace,
        {"deprecated": True, "tag": updated.tag, "image": updated.runtime_image},
        f"Deprecated compatibility command: changed {updated.tag} image to {updated.runtime_image}",
    )
    return 0


def kill(namespace: Any) -> int:
    from luminesk_cli.core.config import UserConfig
    from luminesk_cli.core.manager import ServerManagerError, kill_server

    config = UserConfig.load()

    try:
        result = kill_server(
            config,
            tag=namespace.target,
            force=namespace.force,
            directory=Path.cwd(),
        )
    except ServerManagerError as exc:
        raise RuntimeOperationError(str(exc)) from exc

    emit(
        namespace,
        {
            "deprecated": True,
            "tag": result.target.server.tag,
            "signal": result.signal_name,
        },
        f"Deprecated compatibility command: killed {result.target.server.tag}",
    )
    return 0


def delete(namespace: Any) -> int:
    from luminesk_cli.core.config import UserConfig
    from luminesk_cli.core.manager import ServerManagerError, delete_server

    if not namespace.yes:
        if namespace.non_interactive or namespace.json:
            raise ValidationError("deprecated delete requires --yes")

        answer = input("Remove the legacy Nesk registration and metadata? [y/N] ")

        if answer.strip().lower() not in {"y", "yes"}:
            raise ValidationError("deletion was not confirmed")

    config = UserConfig.load()

    try:
        deleted = delete_server(config, tag=namespace.target, directory=Path.cwd())
    except ServerManagerError as exc:
        raise RuntimeOperationError(str(exc)) from exc

    emit(
        namespace,
        {"deprecated": True, "tag": deleted.tag, "path": str(deleted.path)},
        f"Deprecated compatibility command: removed {deleted.tag} metadata",
    )
    return 0


def list_instances(namespace: Any) -> int:
    from luminesk_cli.core.config import UserConfig
    from luminesk_cli.core.manager import get_runtime_views

    views = get_runtime_views(UserConfig.load())
    entries = [
        {
            "tag": view.server.tag,
            "name": view.server.name,
            "path": str(view.server.path),
            "core": view.server.core_id,
            "status": view.status,
        }
        for view in views
        if (namespace.tag is None or view.server.tag == namespace.tag)
        and (namespace.core is None or view.server.core_id == namespace.core)
        and (namespace.status is None or view.status == namespace.status)
    ]
    emit(
        namespace,
        {"deprecated": True, "instances": entries},
        "\n".join(
            f"{entry['tag']}: {entry['status']} — {entry['path']}"
            for entry in entries
        )
        or "No legacy instances found.",
    )
    return 0


def change_language(namespace: Any) -> int:
    from luminesk_cli.core.config import UserConfig
    from luminesk_cli.core.messages import normalize_language

    config = UserConfig.load()
    config.language = normalize_language(namespace.language)
    config.save()
    emit(
        namespace,
        {"deprecated": True, "language": config.language},
        f"Deprecated compatibility setting: language={config.language}",
    )
    return 0
