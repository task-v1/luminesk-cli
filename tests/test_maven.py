from xml.etree import ElementTree as ET

import httpx
import pytest

from luminesk.models.registry import Maven
from luminesk.utils import maven
from luminesk.utils.download_models import CoreDownloadInfo


def test_get_metadata_url() -> None:
    core = Maven(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://repo.example.com/maven/",
        group_id="org.example.group",
        artifact_id="my-artifact",
    )
    assert (
        maven.get_metadata_url(core)
        == "https://repo.example.com/maven/org/example/group/my-artifact/maven-metadata.xml"
    )


def test_require_maven_coordinates_raises() -> None:
    core_missing_group = Maven(
        id="a",
        name="a",
        description={"en": "a"},
        url="http://a",
        group_id="",
        artifact_id="a",
    )

    with pytest.raises(ValueError, match="missing group_id"):
        maven._require_maven_coordinates(core_missing_group)

    core_missing_artifact = Maven(
        id="a",
        name="a",
        description={"en": "a"},
        url="http://a",
        group_id="g",
        artifact_id="",
    )

    with pytest.raises(ValueError, match="missing artifact_id"):
        maven._require_maven_coordinates(core_missing_artifact)

    core_missing_url = Maven(
        id="a", name="a", description={"en": "a"}, url="", group_id="g", artifact_id="a"
    )

    with pytest.raises(ValueError, match="missing url"):
        maven._require_maven_coordinates(core_missing_url)


def test_strip_namespaces() -> None:
    xml_data = b'<metadata xmlns="http://maven.apache.org/METADATA/1.1.0"><versioning><latest>1.0.0</latest></versioning></metadata>'
    root = ET.fromstring(xml_data)
    stripped = maven._strip_namespaces(root)
    assert stripped.tag == "metadata"
    assert stripped.find("versioning") is not None

    latest = stripped.find("versioning/latest")
    assert latest is not None
    assert latest.text == "1.0.0"


def test_get_latest_version() -> None:
    # release tag preferred
    xml1 = ET.fromstring(
        b"<metadata><versioning><release>2.0.0</release><latest>2.1.0</latest></versioning></metadata>"
    )
    assert maven._get_latest_version(xml1) == "2.0.0"

    # latest tag fallback
    xml2 = ET.fromstring(
        b"<metadata><versioning><latest>2.1.0</latest></versioning></metadata>"
    )
    assert maven._get_latest_version(xml2) == "2.1.0"

    # versions list fallback
    xml3 = ET.fromstring(
        b"<metadata><versioning><versions><version>1.0</version><version>1.5</version></versions></versioning></metadata>"
    )
    assert maven._get_latest_version(xml3) == "1.5"

    # direct version fallback
    xml4 = ET.fromstring(
        b"<metadata><versioning></versioning><version>1.2.3</version></metadata>"
    )
    assert maven._get_latest_version(xml4) == "1.2.3"

    # missing raising error
    xml5 = ET.fromstring(b"<metadata></metadata>")

    with pytest.raises(ValueError, match="missing the versioning section"):
        maven._get_latest_version(xml5)


def test_get_snapshot_resolved_version_with_classifier() -> None:
    xml_data = b"""<metadata>
		<versioning>
			<snapshotVersions>
				<snapshotVersion>
					<classifier>shaded</classifier>
					<extension>jar</extension>
					<value>1.0.0-20260606.120000-1</value>
				</snapshotVersion>
				<snapshotVersion>
					<classifier></classifier>
					<extension>jar</extension>
					<value>1.0.0-20260606.120000-2</value>
				</snapshotVersion>
			</snapshotVersions>
		</versioning>
	</metadata>"""
    root = ET.fromstring(xml_data)
    assert (
        maven._get_snapshot_resolved_version(root, "shaded")
        == "1.0.0-20260606.120000-1"
    )
    assert maven._get_snapshot_resolved_version(root, None) == "1.0.0-20260606.120000-2"

    with pytest.raises(
        ValueError, match="Snapshot metadata does not contain a JAR with classifier"
    ):
        maven._get_snapshot_resolved_version(root, "missing-classifier")


def test_get_snapshot_resolved_version_fallback() -> None:
    xml_data = b"""<metadata>
		<version>1.0.0-SNAPSHOT</version>
		<versioning>
			<snapshot>
				<timestamp>20260606.120000</timestamp>
				<buildNumber>5</buildNumber>
			</snapshot>
		</versioning>
	</metadata>"""
    root = ET.fromstring(xml_data)
    assert maven._get_snapshot_resolved_version(root, None) == "1.0.0-20260606.120000-5"


def test_get_snapshot_resolved_version_missing_raises() -> None:
    xml_data = b"<metadata></metadata>"
    root = ET.fromstring(xml_data)

    with pytest.raises(ValueError, match="missing the versioning section"):
        maven._get_snapshot_resolved_version(root, None)


def test_build_artifact_url() -> None:
    core = Maven(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://repo.example.com/maven/",
        group_id="org.example.group",
        artifact_id="my-artifact",
        classifier="shaded",
    )
    url = maven._build_artifact_url(core, "1.0.0", "1.0.0-20260606.120000-1")
    assert (
        url
        == "https://repo.example.com/maven/org/example/group/my-artifact/1.0.0/my-artifact-1.0.0-20260606.120000-1-shaded.jar"
    )


def test_maven_fetch_xml_rejects_large_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-length": str(maven.MAX_MAVEN_METADATA_BYTES + 1)},
            content=b"<metadata />",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError, match="larger than the safety limit"):
        maven._fetch_xml(client, "https://example.com/maven-metadata.xml")


def test_maven_fetch_xml_malformed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<malformed-xml", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError, match="Invalid XML"):
        maven._fetch_xml(client, "https://example.com/maven-metadata.xml")


def test_get_latest_download_info_release() -> None:
    core = Maven(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://repo.example.com/maven/",
        group_id="org.example.group",
        artifact_id="my-artifact",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("maven-metadata.xml"):
            xml_data = (
                b"<metadata><versioning><release>1.2.3</release></versioning></metadata>"
            )
            return httpx.Response(200, content=xml_data, request=request)
        elif request.url.path.endswith(".sha1"):
            return httpx.Response(200, text="1234567890123456789012345678901234567890", request=request)
        return httpx.Response(444, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    info = maven.get_latest_download_info(core, client=client)

    assert isinstance(info, CoreDownloadInfo)
    assert info.hash == "1234567890123456789012345678901234567890"
    assert (
        info.url
        == "https://repo.example.com/maven/org/example/group/my-artifact/1.2.3/my-artifact-1.2.3.jar"
    )


def test_get_latest_download_url_helper() -> None:
    core = Maven(
        id="test-core",
        name="Test Core",
        description={"en": "Test description"},
        url="https://repo.example.com/maven/",
        group_id="org.example.group",
        artifact_id="my-artifact",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("maven-metadata.xml"):
            xml_data = (
                b"<metadata><versioning><release>1.2.3</release></versioning></metadata>"
            )
            return httpx.Response(200, content=xml_data, request=request)
        elif request.url.path.endswith(".sha1"):
            return httpx.Response(200, text="1234567890123456789012345678901234567890", request=request)
        return httpx.Response(444, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    url = maven.get_latest_download_url(core, client=client)
    assert (
        url
        == "https://repo.example.com/maven/org/example/group/my-artifact/1.2.3/my-artifact-1.2.3.jar"
    )
