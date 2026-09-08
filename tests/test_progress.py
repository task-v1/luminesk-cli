from __future__ import annotations

from argparse import Namespace
from typing import Any

import pytest
from rich.text import Text

from luminesk_cli.cli import progress


class FakeStatus:
    def __init__(self, rendered: Text) -> None:
        self.rendered = [rendered]
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def update(self, rendered: Text) -> None:
        self.rendered.append(rendered)

    def stop(self) -> None:
        self.stopped = True


class FakeConsole:
    def __init__(self) -> None:
        self.created: list[tuple[FakeStatus, dict[str, Any]]] = []

    def status(self, rendered: Text, **kwargs: Any) -> FakeStatus:
        status = FakeStatus(rendered)
        self.created.append((status, kwargs))
        return status


def _namespace(**overrides: bool) -> Namespace:
    values = {
        "json": False,
        "non_interactive": False,
        "debug": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_activity_starts_updates_and_stops_spinner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = FakeConsole()
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: True)
    monkeypatch.setattr(progress.random, "choice", lambda values: values[0])
    monkeypatch.setattr(progress, "_console", lambda: console)

    with progress.activity(_namespace(), "Resolving sources") as current:
        current.update("Building package")

    status, options = console.created[0]
    assert status.started is True
    assert status.stopped is True
    assert [item.plain for item in status.rendered] == [
        "Resolving sources (This may be a good time to grab an iced tea.)",
        "Building package (This may be a good time to grab an iced tea.)",
    ]
    assert options["spinner"] == "dots"


def test_activity_stops_spinner_when_operation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = FakeConsole()
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: True)
    monkeypatch.setattr(progress, "_console", lambda: console)

    with pytest.raises(RuntimeError, match="failed"):
        with progress.activity(_namespace(), "Working"):
            raise RuntimeError("failed")

    assert console.created[0][0].stopped is True


@pytest.mark.parametrize(
    "namespace",
    [
        _namespace(json=True),
        _namespace(non_interactive=True),
        _namespace(debug=True),
    ],
)
def test_activity_is_silent_for_automation_and_debug(
    namespace: Namespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: True)
    monkeypatch.setattr(
        progress,
        "_console",
        lambda: pytest.fail("disabled activity created a console"),
    )

    with progress.activity(namespace, "Working") as current:
        current.update("Still working")


def test_activity_is_silent_without_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(progress.sys.stderr, "isatty", lambda: False)
    monkeypatch.setattr(
        progress,
        "_console",
        lambda: pytest.fail("non-TTY activity created a console"),
    )

    with progress.activity(_namespace(), "Working"):
        pass
