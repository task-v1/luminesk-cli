import pytest

from luminesk.models.registry import CoreProvider, GitHubRelease, Jenkins, Maven
from luminesk.utils import downloads, github_releases, jenkins, maven


def test_get_availability_check_url_unsupported_type() -> None:
    class UnknownProvider(CoreProvider):
        pass

    core = UnknownProvider(
        id="dummy",
        name="Dummy",
        description={"en": "Dummy"},
        url="https://example.com",
    )

    with pytest.raises(ValueError):
        downloads.get_availability_check_url(core)


def test_get_availability_check_url_maven(monkeypatch: pytest.MonkeyPatch) -> None:
    core = Maven(
        id="nukkit",
        name="Nukkit",
        description={"en": "desc"},
        url="https://example.com",
        group_id="g",
        artifact_id="a",
    )
    monkeypatch.setattr(
        maven, "get_metadata_url", lambda _: "https://example.com/meta.xml"
    )
    assert downloads.get_availability_check_url(core) == "https://example.com/meta.xml"


def test_get_availability_check_url_jenkins(monkeypatch: pytest.MonkeyPatch) -> None:
    core = Jenkins(
        id="mot",
        name="MOT",
        description={"en": "desc"},
        url="https://example.com",
    )
    monkeypatch.setattr(
        jenkins, "get_build_info_url", lambda _: "https://example.com/build.json"
    )
    assert (
        downloads.get_availability_check_url(core) == "https://example.com/build.json"
    )


def test_get_availability_check_url_github(monkeypatch: pytest.MonkeyPatch) -> None:
    core = GitHubRelease(
        id="lumi",
        name="Lumi",
        description={"en": "desc"},
        url="https://github.com/example/repo",
        release_file="Lumi-*.jar",
    )
    monkeypatch.setattr(
        github_releases, "get_release_api_url", lambda _: "https://api.example/releases"
    )
    assert downloads.get_availability_check_url(core) == "https://api.example/releases"
