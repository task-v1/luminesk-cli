import httpx
import pytest

from luminesk.models.registry import Jenkins
from luminesk.utils import jenkins
from luminesk.utils.download_models import CoreDownloadInfo


def test_get_build_info_url() -> None:
    core = Jenkins(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://jenkins.example.com/job/test-job/",
    )
    assert (
        jenkins.get_build_info_url(core)
        == "https://jenkins.example.com/job/test-job/lastSuccessfulBuild/api/json"
    )


def test_require_jenkins_job_url_raises_if_empty() -> None:
    core = Jenkins(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="",
    )

    with pytest.raises(ValueError, match="missing url"):
        jenkins._require_jenkins_job_url(core)


def test_select_jenkins_artifact_no_classifier() -> None:
    artifacts = [
        {"relativePath": "dir/aux-sources.jar", "fileName": "aux-sources.jar"},
        {"relativePath": "dir/primary.jar", "fileName": "primary.jar"},
        {"relativePath": "dir/other-tests.jar", "fileName": "other-tests.jar"},
    ]
    assert jenkins._select_jenkins_artifact(artifacts, None) == "dir/primary.jar"


def test_select_jenkins_artifact_with_classifier() -> None:
    artifacts = [
        {"relativePath": "dir/primary.jar", "fileName": "primary.jar"},
        {"relativePath": "dir/primary-shaded.jar", "fileName": "primary-shaded.jar"},
    ]
    assert (
        jenkins._select_jenkins_artifact(artifacts, "shaded")
        == "dir/primary-shaded.jar"
    )


def test_select_jenkins_artifact_missing_classifier() -> None:
    artifacts = [
        {"relativePath": "dir/primary.jar", "fileName": "primary.jar"},
    ]

    with pytest.raises(ValueError, match="No JAR with classifier"):
        jenkins._select_jenkins_artifact(artifacts, "shaded")


def test_select_jenkins_artifact_no_jars() -> None:
    artifacts = [
        {"relativePath": "dir/primary.zip", "fileName": "primary.zip"},
    ]

    with pytest.raises(ValueError, match="No JAR artifacts"):
        jenkins._select_jenkins_artifact(artifacts, None)


def test_select_jenkins_artifact_missing_primary() -> None:
    artifacts = [
        {"relativePath": "dir/primary-sources.jar", "fileName": "primary-sources.jar"},
    ]

    with pytest.raises(ValueError, match="No primary JAR artifact"):
        jenkins._select_jenkins_artifact(artifacts, None)


def test_get_build_version_from_number() -> None:
    build_info = {"number": 123}
    assert jenkins._get_build_version(build_info) == "build-123"


def test_get_build_version_from_id_or_display_name() -> None:
    assert jenkins._get_build_version({"id": "custom-id"}) == "custom-id"
    assert jenkins._get_build_version({"displayName": "Custom Build"}) == "Custom Build"
    assert jenkins._get_build_version({}) == "latest"


def test_get_latest_download_info_success() -> None:
    core = Jenkins(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://jenkins.example.com/job/test-job/",
        classifier="shaded",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert (
            request.url
            == "https://jenkins.example.com/job/test-job/lastSuccessfulBuild/api/json"
        )
        payload = {
            "number": 42,
            "artifacts": [
                {"relativePath": "test-42.jar", "fileName": "test-42.jar"},
                {
                    "relativePath": "test-42-shaded.jar",
                    "fileName": "test-42-shaded.jar",
                },
            ],
            "actions": [
                {
                    "lastBuiltRevision": {
                        "SHA1": "abcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde"
                    }
                }
            ],
        }
        return httpx.Response(200, json=payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    info = jenkins.get_latest_download_info(core, client=client)

    assert isinstance(info, CoreDownloadInfo)
    assert (
        info.url
        == "https://jenkins.example.com/job/test-job/lastSuccessfulBuild/artifact/test-42-shaded.jar"
    )
    assert info.hash == "abcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde"


def test_get_latest_download_url_helper() -> None:
    core = Jenkins(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://jenkins.example.com/job/test-job/",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "number": 42,
            "artifacts": [
                {"relativePath": "test-42.jar", "fileName": "test-42.jar"},
            ],
        }
        return httpx.Response(200, json=payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    url = jenkins.get_latest_download_url(core, client=client)
    assert (
        url
        == "https://jenkins.example.com/job/test-job/lastSuccessfulBuild/artifact/test-42.jar"
    )
