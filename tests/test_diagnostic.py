from luminesk.core import diagnostic


class FakeCore:
    def __init__(self, core_id: str, name: str, url: str) -> None:
        self.id = core_id
        self.name = name
        self._url = url
        self._provider = self

    def get_availability_check_url(self) -> str:
        if self._url == "raise":
            raise RuntimeError("source unavailable")

        return self._url


def test_check_repositories_preserves_registry_order(monkeypatch) -> None:
    cores = [
        FakeCore("first", "First", "https://example.com/first"),
        FakeCore("second", "Second", "https://example.com/second"),
    ]

    def fake_check_source(
        client, core_name: str, check_url: str
    ) -> diagnostic.DiagnosticResult:
        return diagnostic.DiagnosticResult(
            name=core_name, status=True, message=check_url
        )

    monkeypatch.setattr(diagnostic.registry, "get_all", lambda: cores)
    monkeypatch.setattr(diagnostic, "_check_source", fake_check_source)

    results = diagnostic.check_repositories()

    assert [result.name for result in results] == ["First", "Second"]
    assert [result.message for result in results] == [
        "https://example.com/first",
        "https://example.com/second",
    ]


def test_check_repositories_wraps_source_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostic.registry,
        "get_all",
        lambda: [FakeCore("broken", "Broken", "raise")],
    )

    result = diagnostic.check_repositories()[0]

    assert result.name == "Broken Source"
    assert not result.status
    assert "source unavailable" in result.message
