from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, TextIO

from cyclopts import App, Parameter
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from luminesk.core import diagnostic as dg
from luminesk.core import manager as srv
from luminesk.core.config import UserConfig
from luminesk.core.messages import MESSAGE_CATALOGS, normalize_language, set_language, t
from luminesk.core.registry import registry
from luminesk.main import __version__
from luminesk.utils.docker import (
    DEFAULT_DOCKER_MEMORY_LIMIT,
    DEFAULT_FALLBACK_IMAGE,
    normalize_memory_limit,
    normalize_runtime_image,
)
from luminesk.utils.rich_utils import (
    accent,
    ansi_text,
    danger,
    emph,
    error_panel,
    format_kv,
    format_server,
    info_panel,
    muted,
    success,
    success_panel,
    warning,
)

NameOption = Annotated[
    str | None, Parameter(name=["--name", "-n"], help=t("cli.create.option.name"))
]
DirectoryOption = Annotated[
    Path | None, Parameter(name=["--dir", "-d"], help=t("cli.create.option.directory"))
]
CoreOption = Annotated[
    str | None, Parameter(name=["--core", "-c"], help=t("cli.create.option.core"))
]
TagOption = Annotated[
    str | None, Parameter(name=["--tag", "-t"], help=t("cli.create.option.tag"))
]
ForceOption = Annotated[
    bool, Parameter(name=["--force", "-f"], help=t("cli.create.option.force"))
]
MemoryOption = Annotated[
    str, Parameter(name=["--memory", "-m"], help=t("cli.create.option.memory"))
]
ImageOption = Annotated[
    str | None, Parameter(name=["--image", "-i"], help=t("cli.create.option.image"))
]
StartTagArgument = Annotated[str | None, Parameter(help=t("cli.start.argument.tag"))]

app = App(
    name="nesk",
    help="Luminesk: MCBE server composer.",
    version=t("cli.version.banner", version=__version__),
    version_flags=["--version", "-v"],
    default_parameter=Parameter(negative=""),
)
console = Console()


def _load_cli_config() -> UserConfig:
    try:
        config = UserConfig.load()
    except Exception as exc:
        console.print(error_panel(t("cli.config.load_failed", error=exc)))
        raise SystemExit(1) from exc

    set_language(config.language)
    _translate_cli_help()
    return config


def init_cli_language() -> None:
    try:
        config = UserConfig.load()
        lang = config.language
    except Exception:
        lang = "en"

    set_language(lang)
    _translate_cli_help()


def _translate_cli_help() -> None:
    app.help = t("cli.help.app")
    app.version = t("cli.version.banner", version=__version__)

    command_keys = {
        "diagnostic": "cli.help.diagnostic",
        "cores": "cli.help.cores",
        "create": "cli.help.create",
        "start": "cli.help.start",
        "attach": "cli.help.attach",
        "upgrade-core": "cli.help.upgrade_core",
        "change-image": "cli.help.change_image",
        "stop": "cli.help.stop",
        "kill": "cli.help.kill",
        "delete": "cli.help.delete",
        "list": "cli.help.list",
        "change-lang": "cli.help.change_lang",
        "--help": "cli.help.help",
        "-h": "cli.help.help",
        "--version": "cli.help.version",
        "-v": "cli.help.version",
    }

    for name, cmd_app in app._commands.items():
        if name in command_keys:
            cmd_app.help = t(command_keys[name])


ANSI_ESCAPE_RE = re.compile(r"(\x1b\[[0-9;]*[a-zA-Z])")


def wrap_ansi_for_readline(ansi_str: str) -> str:
    if "readline" in sys.modules:
        return ANSI_ESCAPE_RE.sub(r"\001\1\002", ansi_str)

    return ansi_str


class ReadlinePrompt(Prompt):
    @property
    def illegal_choice_message(self) -> str:
        return t("cli.prompt.invalid_choice")

    @property
    def validate_error_message(self) -> str:
        return t("cli.prompt.invalid_value")

    @classmethod
    def get_input(
        cls,
        console: Console,
        prompt: str | Text,
        password: bool,
        stream: TextIO | None = None,
    ) -> str:
        if password:
            return console.input(prompt, password=password, stream=stream)

        with console.capture() as capture:
            console.print(prompt, end="")

        ansi_prompt = capture.get()

        readline_prompt = wrap_ansi_for_readline(ansi_prompt)

        if stream:
            console.print(prompt, end="")
            return stream.readline()
        else:
            return input(readline_prompt)


def _status_label(status: bool):
    label = t("common.ok") if status else t("common.fail")
    styled = success(label, bold=True) if status else danger(label, bold=True)
    return ansi_text(styled)


@app.command(name="diagnostic", alias=["check", "diag"])
def diagnostic() -> None:
    """Check compatible core repositories."""
    _load_cli_config()
    results = []
    status_text = ansi_text(muted(t("cli.diagnostic.checking_sources")))

    with console.status(status_text, spinner="dots"):
        results.extend(dg.check_repositories())

    table = Table(header_style="bold")
    table.add_column(t("label.component"), no_wrap=True)
    table.add_column(t("label.status"), no_wrap=True)
    table.add_column(t("label.description"))

    for res in results:
        name_text = ansi_text(accent(res.name, bold=True))
        status_text = _status_label(res.status)
        message_text = ansi_text(
            success(res.message) if res.status else danger(res.message)
        )
        table.add_row(name_text, status_text, message_text)

    console.print(table)

    if any(not res.status for res in results):
        console.print(error_panel(danger(t("cli.diagnostic.failure"), bold=True)))
        raise SystemExit(1)

    console.print(success_panel(success(t("cli.diagnostic.success"), bold=True)))


@app.command(name="cores", alias="c")
def cores() -> None:
    """List available cores."""
    _load_cli_config()
    lines = []

    for core in registry.get_all():
        bullet = success("*")
        name = accent(core.name, bold=True)
        description = muted(core.localized_description)
        lines.append(f"{bullet} {name}\n{description}")

    tip = f"\n{emph('Tip:')} {t('cli.cores.tip', command=accent('nesk diagnostic', bold=True))}"
    lines.append(tip)

    console.print(
        Panel(
            ansi_text("\n\n".join(lines)),
            title=t("cli.cores.title"),
            border_style="cyan",
            padding=(1, 2),
        )
    )


@app.command(name="create", alias=["new", "init"])
def create(
    *,
    name: NameOption = None,
    directory: DirectoryOption = None,
    core: CoreOption = None,
    tag: TagOption = None,
    force: ForceOption = False,
    memory: MemoryOption = DEFAULT_DOCKER_MEMORY_LIMIT,
    image: ImageOption = None,
) -> None:
    """Create a new server."""
    config = _load_cli_config()
    full_wizard_mode = all(value is None for value in (name, directory, core, tag))

    if core is None:
        choices = [c.id for c in registry.get_all()]
        core = ReadlinePrompt.ask(
            t("cli.create.prompt.core"),
            choices=choices,
            default=choices[0] if choices else "lumi",
        )

    selected_core = registry.get_by_id(core)

    if selected_core is None:
        console.print(
            error_panel(
                t(
                    "cli.create.core_not_found",
                    core_id=danger(core, bold=True),
                    command=accent("nesk cores", bold=True),
                )
            )
        )
        raise SystemExit(1)

    if name is None:
        name = ReadlinePrompt.ask(
            t("cli.create.prompt.name"),
            default=t("common.default_server_name", core_name=selected_core.name),
        )

    if tag is None:
        base_tag = f"server-{selected_core.id}"
        default_tag = base_tag
        if config.get_server_by_tag(default_tag) is not None:
            counter = 1

            while True:
                default_tag = f"{base_tag}-{counter}"

                if config.get_server_by_tag(default_tag) is None:
                    break

                counter += 1

        import re

        while True:
            tag = ReadlinePrompt.ask(t("cli.create.prompt.tag"), default=default_tag)

            if re.match(r"^[a-zA-Z0-9\-_.]+$", tag):
                break

            console.print(error_panel(t("config.validation.tag_invalid")))

    if directory is None:
        default_directory = (config.default_server_path / tag).expanduser()
        directory = Path(
            ReadlinePrompt.ask(
                t("cli.create.prompt.directory"),
                default=str(default_directory),
            )
        )

    if image is None:
        default_image = selected_core.get_docker_image()
        image = (
            ReadlinePrompt.ask(t("cli.create.prompt.image"), default=default_image)
            if full_wizard_mode
            else default_image
        )

    try:
        memory_limit = normalize_memory_limit(memory)
        default_image = selected_core.get_docker_image()
        if image is not None and image != default_image:
            from luminesk.utils.docker import validate_runtime_image
            runtime_image = validate_runtime_image(image)
        else:
            runtime_image = normalize_runtime_image(image or default_image)
        server = srv.create_server(
            config=config,
            name=name,
            tag=tag,
            directory=directory,
            core=selected_core,
            force=force,
            console=console,
            memory_limit=memory_limit,
            runtime_image=runtime_image,
        )
    except (srv.ServerManagerError, RuntimeError, ValueError) as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    create_details = [
        success(t("cli.create.success_title"), bold=True),
        format_kv(t("label.name"), server.name),
        format_kv(t("label.tag"), server.tag),
        format_kv(t("label.core"), selected_core.name),
        format_kv(t("label.core_hash"), server.core_hash or t("common.unknown")),
        format_kv(t("label.executable"), server.executable_name),
        format_kv(t("label.image"), server.runtime_image),
        format_kv(t("label.memory_limit"), server.memory_limit),
        format_kv(t("label.path"), server.path, dim_value=True),
    ]
    console.print(success_panel("\n".join(create_details)))


@app.command(name="start", alias="s")
def start(
    tag: StartTagArgument = None,
    /,
    *,
    loop: Annotated[
        bool, Parameter(name=["--loop", "-l"], help=t("cli.start.option.loop"))
    ] = False,
    detached: Annotated[
        bool,
        Parameter(
            name=["--detached", "-d"],
            help=t("cli.start.option.detached"),
        ),
    ] = False,
) -> None:
    """Start a server."""
    config = _load_cli_config()

    try:
        server = srv.resolve_server(config=config, tag=tag, directory=Path.cwd())
        exit_code = srv.run_server(
            config=config,
            server=server,
            loop=loop,
            detached=detached,
            console=console,
        )
    except srv.ServerManagerError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    raise SystemExit(exit_code)


@app.command(name="attach", alias="a")
def attach(
    tag: Annotated[str | None, Parameter(help=t("cli.attach.argument.tag"))] = None,
    /,
) -> None:
    """Attach to a running server and follow logs."""
    config = _load_cli_config()

    try:
        server = srv.resolve_server(config=config, tag=tag, directory=Path.cwd())
        exit_code = srv.attach_server(config=config, server=server)
    except srv.ServerManagerError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    raise SystemExit(exit_code)


@app.command(name="upgrade-core", alias="upcore")
def upgrade_core(
    tag: Annotated[str | None, Parameter(help=t("cli.upgrade.option.tag"))] = None,
    /,
    *,
    redownload: Annotated[
        bool,
        Parameter(
            name=["--redownload", "-r"],
            help=t("cli.upgrade.option.redownload"),
        ),
    ] = False,
) -> None:
    """Upgrade the server core to the latest available version."""
    config = _load_cli_config()

    try:
        server = srv.resolve_server(config=config, tag=tag, directory=Path.cwd())
        updated_server, upgraded = srv.upgrade_server_core(
            config=config, server=server, console=console, redownload=redownload
        )
    except srv.ServerManagerError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    if not upgraded:
        console.print(
            info_panel(
                t("cli.upgrade.already_up_to_date"),
                title=t("cli.upgrade.success_title"),
            )
        )
        raise SystemExit(0)

    upgrade_details = [
        success(t("cli.upgrade.success_title"), bold=True),
        format_kv(
            t("label.server"),
            format_server(updated_server.name, updated_server.tag),
            value_color=None,
        ),
        format_kv(t("label.core"), updated_server.core_id),
        format_kv(
            t("label.hash"), updated_server.core_hash or t("common.unknown")
        ),
        format_kv(t("label.executable"), updated_server.executable_name),
    ]
    console.print(success_panel("\n".join(upgrade_details)))


@app.command(name="change-image", alias="image")
def change_image(
    tag: Annotated[str | None, Parameter(help=t("cli.change_image.option.tag"))] = None,
    /,
    *,
    image: Annotated[
        str | None,
        Parameter(name=["--image", "-i"], help=t("cli.change_image.option.image")),
    ] = None,
) -> None:
    """Change the server Docker image."""
    config = _load_cli_config()

    try:
        server = srv.resolve_server(config=config, tag=tag, directory=Path.cwd())
    except srv.ServerManagerError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    if image is None:
        core = registry.get_by_id(server.core_id)
        default_image = (
            core.get_docker_image() if core is not None else DEFAULT_FALLBACK_IMAGE
        )
        image = ReadlinePrompt.ask(t("cli.change_image.prompt.image"), default=default_image)

    try:
        updated_server = srv.change_server_image(
            config=config,
            server=server,
            image=image,
        )
    except srv.ServerManagerError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    image_details = [
        success(t("cli.change_image.success_title"), bold=True),
        format_kv(
            t("label.server"),
            format_server(updated_server.name, updated_server.tag),
            value_color=None,
        ),
        format_kv(t("label.image"), updated_server.runtime_image),
    ]
    console.print(success_panel("\n".join(image_details)))


@app.command(name="stop", alias="st")
def stop(
    tag: Annotated[str | None, Parameter(help=t("cli.stop.argument.tag"))] = None,
    /,
    *,
    force: Annotated[
        bool, Parameter(name=["--force", "-f"], help=t("cli.stop.option.force"))
    ] = False,
) -> None:
    """Gracefully stop a server by tag or PID."""
    _control_server(tag=tag, force=force, action_name="stop")


@app.command(name="kill", alias="k")
def kill(
    tag: Annotated[str | None, Parameter(help=t("cli.kill.argument.tag"))] = None,
    /,
    *,
    force: Annotated[
        bool, Parameter(name=["--force", "-f"], help=t("cli.kill.option.force"))
    ] = False,
) -> None:
    """Force-kill a server by tag or PID."""
    _control_server(tag=tag, force=force, action_name="kill")


@app.command(name="delete", alias="d")
def delete(
    tag: Annotated[str | None, Parameter(help=t("cli.delete.argument.tag"))] = None,
    /,
    *,
    yes: Annotated[
        bool,
        Parameter(
            name=["--yes", "-y"],
            help=t("cli.delete.option.yes"),
        ),
    ] = False,
) -> None:
    """Delete a stopped server from Luminesk."""
    config = _load_cli_config()

    try:
        server = srv.resolve_server(config=config, tag=tag, directory=Path.cwd())
        runtime_view = srv.get_runtime_view(config, server)

        if runtime_view.status == "running" or runtime_view.loop_enabled:
            raise srv.ServerManagerError(
                t("manager.server_must_be_stopped_for_delete", tag=server.tag)
            )

        if not yes:
            console.print(warning(t("cli.delete.warning")))
            confirm = ReadlinePrompt.ask(
                t("cli.delete.prompt", tag=server.tag),
                choices=["y", "n"],
                default="n",
            )

            if confirm.lower() != "y":
                console.print(t("common.cancelled"))
                raise SystemExit(0)

        deleted_server = srv.delete_server(config=config, tag=server.tag, directory=Path.cwd())
    except srv.ServerManagerError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    delete_details = [
        success(t("cli.delete.success_title"), bold=True),
        format_kv(
            t("label.server"), format_server(deleted_server.name, deleted_server.tag), value_color=None
        ),
        format_kv(t("label.path"), deleted_server.path, dim_value=True),
    ]
    console.print(success_panel("\n".join(delete_details)))


@app.command(name="list", alias=["ls", "l"])
def list_servers(
    *,
    tag: Annotated[
        str | None, Parameter(name=["--tag", "-t"], help=t("cli.list.option.tag"))
    ] = None,
    status: Annotated[
        str | None, Parameter(name=["--status", "-s"], help=t("cli.list.option.status"))
    ] = None,
    core: Annotated[
        str | None, Parameter(name=["--core", "-c"], help=t("cli.list.option.core"))
    ] = None,
) -> None:
    """List servers and their status."""
    config = _load_cli_config()

    try:
        status_filter = _normalize_status_filter(status)
    except ValueError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    views = srv.get_runtime_views(config)

    filtered_views = [
        view
        for view in views
        if (tag is None or view.server.tag == tag.strip().lower())
        and (status_filter is None or view.status == status_filter)
        and (core is None or view.server.core_id == core.strip().lower())
    ]

    if not views:
        console.print(info_panel(t("cli.list.no_servers")))
        return

    if not filtered_views:
        console.print(info_panel(t("cli.list.no_matches")))
        return

    table = Table(title=t("cli.list.title"), header_style="bold")
    table.add_column(t("label.tag"), no_wrap=True)
    table.add_column(t("label.name"))
    table.add_column(t("label.core"), no_wrap=True)
    table.add_column(t("label.image"), no_wrap=True)
    table.add_column(t("label.status"), no_wrap=True)
    table.add_column(t("label.pid"), no_wrap=True, justify="right")
    table.add_column(t("label.uptime"), no_wrap=True)
    table.add_column(t("label.last_start"), no_wrap=True)
    table.add_column(t("label.last_stop"), no_wrap=True)
    table.add_column(t("label.path"), overflow="fold")

    for view in filtered_views:
        pid_value = str(view.pid) if view.pid is not None else t("common.empty")
        pid_text = muted(pid_value) if view.pid is None else pid_value

        uptime_value = srv.format_timedelta(view.uptime)
        uptime_text = muted(uptime_value) if view.uptime is None else uptime_value

        last_started = _format_datetime(view.last_started_at)
        last_started_text = (
            muted(last_started) if view.last_started_at is None else last_started
        )

        last_stopped = _format_datetime(view.last_stopped_at)
        last_stopped_text = (
            muted(last_stopped) if view.last_stopped_at is None else last_stopped
        )

        table.add_row(
            ansi_text(accent(view.server.tag, bold=True)),
            ansi_text(emph(view.server.name)),
            ansi_text(accent(view.server.core_id)),
            ansi_text(accent(view.server.runtime_image)),
            _format_status(view.status, view.loop_enabled, view.docker_container_name),
            ansi_text(pid_text),
            ansi_text(uptime_text),
            ansi_text(last_started_text),
            ansi_text(last_stopped_text),
            ansi_text(muted(str(view.server.path))),
        )

    console.print(table)


@app.command(name="change-lang", alias=["lang"])
def change_lang(
    lang: Annotated[
        str | None, Parameter(help=t("cli.change_lang.argument.lang"))
    ] = None,
    /,
) -> None:
    """Change the CLI language."""
    config = _load_cli_config()

    if lang is None:
        available_langs = ", ".join(MESSAGE_CATALOGS.keys())
        console.print(
            info_panel(
                f"{t('cli.change_lang.current', lang=config.language)}\n"
                f"{t('cli.change_lang.available', langs=available_langs)}"
            )
        )
        return

    normalized_lang = normalize_language(lang)

    if lang.strip().lower() not in MESSAGE_CATALOGS:
        console.print(error_panel(t("cli.change_lang.invalid", lang=lang)))
        raise SystemExit(1)

    config.language = normalized_lang
    config.save()
    set_language(normalized_lang)
    _translate_cli_help()
    console.print(success_panel(t("cli.change_lang.success", lang=normalized_lang)))


def _control_server(
    tag: str | None = None,
    force: bool = False,
    action_name: str = "stop",
) -> None:
    config = _load_cli_config()

    status_message = (
        t("launcher.killing_server")
        if action_name == "kill"
        else t("launcher.stopping_server")
    )

    try:
        with console.status(ansi_text(muted(status_message)), spinner="dots"):
            if action_name == "kill":
                result = srv.kill_server(
                    config=config,
                    tag=tag,
                    force=force,
                    directory=Path.cwd(),
                )
            else:
                result = srv.stop_server(
                    config=config,
                    tag=tag,
                    force=force,
                    directory=Path.cwd(),
                )
    except srv.ServerManagerError as exc:
        console.print(error_panel(str(exc)))
        raise SystemExit(1) from exc

    if result.loop_active and not force:
        console.print(
            info_panel(
                t(
                    "cli.control.loop_warning",
                    tag=accent(result.target.server.tag, bold=True),
                    force_flag=warning("--force", bold=True),
                )
            )
        )

    details = [
        format_kv(t("label.action"), action_name, bold_value=True),
        format_kv(
            t("label.server"),
            format_server(result.target.server.name, result.target.server.tag),
            value_color=None,
        ),
        format_kv(t("label.signal"), result.signal_name),
    ]

    if result.signaled_server and result.server_pid is not None:
        details.append(format_kv(t("label.server_pid"), result.server_pid))

    console.print(success_panel("\n".join(details)))


def _normalize_status_filter(status: str | None) -> str | None:
    if status is None:
        return None

    normalized_status = status.strip().lower()

    if normalized_status not in {"running", "stopped"}:
        raise ValueError(t("cli.status.invalid"))

    return normalized_status


def _format_status(
    status: str,
    loop_enabled: bool,
    docker_container_name: str | None = None,
) -> Text:
    suffixes = []

    if loop_enabled:
        suffixes.append(warning(t("common.loop")))

    if docker_container_name is not None:
        suffixes.append(
            accent(t("common.docker_container", container_name=docker_container_name))
        )

    suffix = f" ({', '.join(suffixes)})" if suffixes else ""

    if status == "running":
        return ansi_text(success(t("common.running"), bold=True) + suffix)

    return ansi_text(danger(t("common.stopped"), bold=True) + suffix)


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return t("common.empty")

    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")
