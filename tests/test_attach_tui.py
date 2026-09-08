from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput

from luminesk_cli.application.runtime import AttachSession, DockerRuntime
from luminesk_cli.cli.attach_tui import AttachTui, run_attach_tui
from luminesk_cli.domain.errors import RuntimeOperationError, ValidationError


class FakeProcessOutput:
    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self._chunks = chunks or []

    async def read(self, size: int = -1) -> bytes:
        del size
        return self._chunks.pop(0) if self._chunks else b""


class FakeProcessInput:
    def __init__(self, process: FakeProcess) -> None:
        self._process = process
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)
        if data == b"\x04":
            self._process.finish(0)

    async def drain(self) -> None:
        return None


class FakeProcess:
    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self.stdout = FakeProcessOutput(chunks)
        self.returncode: int | None = None
        self._finished = asyncio.Event()
        self.stdin = FakeProcessInput(self)

    async def wait(self) -> int:
        await self._finished.wait()
        assert self.returncode is not None
        return self.returncode

    def terminate(self) -> None:
        self.finish(0)

    def finish(self, returncode: int) -> None:
        if self.returncode is None:
            self.returncode = returncode
            self._finished.set()


def _session() -> AttachSession:
    return AttachSession(
        argv=("docker", "attach", "container-id"),
        history="old output\n",
        tag="fixture",
    )


def test_attach_tui_sends_commands_and_detaches_without_stopping_server(
    tmp_path: Path,
) -> None:
    async def scenario() -> tuple[int, FakeProcess, list[tuple[str, ...]]]:
        process = FakeProcess([b"new output\n"])
        calls: list[tuple[str, ...]] = []

        async def process_factory(argv: tuple[str, ...]) -> FakeProcess:
            calls.append(argv)
            return process

        with create_pipe_input() as pipe_input:
            tui = AttachTui(
                tmp_path,
                DockerRuntime(),
                _session(),
                process_factory=process_factory,
                input=pipe_input,
                output=DummyOutput(),
            )
            task = asyncio.create_task(tui.run())
            await asyncio.sleep(0.05)
            pipe_input.send_text("say hello\r")
            await asyncio.sleep(0.05)
            pipe_input.send_bytes(b"\x04")
            result = await asyncio.wait_for(task, 2)
        return result, process, calls

    result, process, calls = asyncio.run(scenario())

    assert result == 0
    assert calls == [_session().argv]
    assert process.stdin.writes == [b"say hello\n", b"\x04"]


@pytest.mark.parametrize(
    ("key", "method_name"),
    [(b"\x03", "stop"), (b"\x0b", "kill")],
)
def test_attach_tui_runtime_hotkeys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    key: bytes,
    method_name: str,
) -> None:
    async def scenario() -> int:
        process = FakeProcess()

        async def process_factory(argv: tuple[str, ...]) -> FakeProcess:
            del argv
            return process

        runtime = DockerRuntime()
        calls: list[Path] = []
        monkeypatch.setattr(
            runtime,
            method_name,
            lambda root, **kwargs: calls.append(root),
        )
        with create_pipe_input() as pipe_input:
            tui = AttachTui(
                tmp_path,
                runtime,
                _session(),
                process_factory=process_factory,
                input=pipe_input,
                output=DummyOutput(),
            )
            task = asyncio.create_task(tui.run())
            await asyncio.sleep(0.05)
            pipe_input.send_bytes(key)
            result = await asyncio.wait_for(task, 2)
        assert calls == [tmp_path]
        return result

    assert asyncio.run(scenario()) == 0


def test_attach_tui_requires_real_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_stream = type("FakeStream", (), {"isatty": lambda self: False})()
    runtime = DockerRuntime()
    monkeypatch.setattr("luminesk_cli.cli.attach_tui.sys.stdin", fake_stream)
    monkeypatch.setattr("luminesk_cli.cli.attach_tui.sys.stdout", fake_stream)

    with pytest.raises(ValidationError, match="interactive TTY"):
        run_attach_tui(tmp_path, runtime)


def test_attach_tui_reports_process_start_failure(tmp_path: Path) -> None:
    async def process_factory(argv: tuple[str, ...]) -> FakeProcess:
        del argv
        raise OSError("docker missing")

    tui = AttachTui(
        tmp_path,
        DockerRuntime(),
        _session(),
        process_factory=process_factory,
        output=DummyOutput(),
    )

    with pytest.raises(RuntimeOperationError, match="cannot attach to Docker"):
        asyncio.run(tui.run())


def test_attach_tui_preserves_nonzero_docker_exit_code(tmp_path: Path) -> None:
    async def scenario() -> None:
        process = FakeProcess()
        process.finish(17)

        async def process_factory(argv: tuple[str, ...]) -> FakeProcess:
            del argv
            return process

        with create_pipe_input() as pipe_input:
            tui = AttachTui(
                tmp_path,
                DockerRuntime(),
                _session(),
                process_factory=process_factory,
                input=pipe_input,
                output=DummyOutput(),
            )
            task = asyncio.create_task(tui.run())
            await asyncio.sleep(0.05)
            pipe_input.send_bytes(b"\x04")
            with pytest.raises(RuntimeOperationError) as raised:
                await asyncio.wait_for(task, 2)
        assert raised.value.details["exitCode"] == 17

    asyncio.run(scenario())
