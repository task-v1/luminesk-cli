from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import httpx

from luminesk.core.messages import t
from luminesk.models.registry import Maven
from luminesk.utils.download_models import CoreDownloadInfo
from luminesk.utils.errors import format_error
from luminesk.utils.http import request_with_retries

MAX_MAVEN_METADATA_BYTES = 2 * 1024 * 1024


def get_metadata_url(core: Maven) -> str:
    group_id, artifact_id, repo_url = _require_maven_coordinates(core)
    group_path = group_id.replace(".", "/")
    repo_url = repo_url.rstrip("/")

    return f"{repo_url}/{group_path}/{artifact_id}/maven-metadata.xml"


def get_latest_download_url(core: Maven, client: httpx.Client | None = None) -> str:
    return get_latest_download_info(core, client=client).url


def get_latest_download_info(
    core: Maven, client: httpx.Client | None = None
) -> CoreDownloadInfo:
    if client is not None:
        return _get_latest_download_info(client, core)

    with httpx.Client(timeout=10.0, follow_redirects=True) as owned_client:
        return _get_latest_download_info(owned_client, core)


def _get_latest_download_info(client: httpx.Client, core: Maven) -> CoreDownloadInfo:
    metadata_xml = _fetch_xml(client, get_metadata_url(core))
    version = _get_latest_version(metadata_xml)

    if core.is_snapshot or version.endswith("-SNAPSHOT"):
        resolved_version = _get_snapshot_resolved_version(
            _fetch_xml(client, _build_version_metadata_url(core, version)),
            core.classifier,
        )
        jar_url = _build_artifact_url(core, version, resolved_version)
    else:
        jar_url = _build_artifact_url(core, version, version)

    sha1_url = jar_url + ".sha1"

    try:
        response = client.get(sha1_url)
        response.raise_for_status()
        sha1_hash = response.text.strip().split()[0].lower()
    except Exception as exc:
        raise ValueError(
            t("maven.fetch_xml_error", url=sha1_url, error=str(exc))
        )

    return CoreDownloadInfo(
        url=jar_url,
        hash=sha1_hash,
    )


def _fetch_xml(client: httpx.Client, url: str) -> Element:
    try:
        response = request_with_retries(
            client,
            "GET",
            url,
            raise_for_status=True,
            retry_on_status=True,
        )
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            t("maven.fetch_xml_http", url=url, status_code=exc.response.status_code)
        ) from exc
    except httpx.RequestError as exc:
        raise ValueError(
            t("maven.fetch_xml_error", url=url, error=format_error(exc))
        ) from exc

    content_length = response.headers.get("content-length")

    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = None
        if declared_size is not None and declared_size > MAX_MAVEN_METADATA_BYTES:
            raise ValueError(t("maven.xml_too_large", url=url))

    if len(response.content) > MAX_MAVEN_METADATA_BYTES:
        raise ValueError(t("maven.xml_too_large", url=url))

    try:
        return _strip_namespaces(ET.fromstring(response.content))
    except ET.ParseError as exc:
        raise ValueError(t("maven.invalid_xml", url=url)) from exc


def _strip_namespaces(element: Element) -> Element:
    for node in element.iter():
        if isinstance(node.tag, str) and "}" in node.tag:
            node.tag = node.tag.rsplit("}", 1)[-1]

    return element


def _get_latest_version(metadata: Element) -> str:
    versioning = metadata.find("versioning")

    if versioning is None:
        raise ValueError(t("maven.versioning_missing"))

    preferred_tags = ("release", "latest", "snapshot")

    for tag in preferred_tags:
        value = versioning.findtext(tag)
        if value:
            return value.strip()

    versions = [
        version.text.strip()
        for version in versioning.findall("versions/version")
        if version.text and version.text.strip()
    ]

    if versions:
        return versions[-1]

    direct_version = metadata.findtext("version")

    if direct_version and direct_version.strip():
        return direct_version.strip()

    raise ValueError(t("maven.latest_version_missing"))


def _build_version_metadata_url(core: Maven, version: str) -> str:
    group_id, artifact_id, repo_url = _require_maven_coordinates(core)
    group_path = group_id.replace(".", "/")
    repo_url = repo_url.rstrip("/")

    return f"{repo_url}/{group_path}/{artifact_id}/{version}/maven-metadata.xml"


def _get_snapshot_resolved_version(
    metadata: Element, classifier: str | None = None
) -> str:
    versioning = metadata.find("versioning")

    if versioning is None:
        raise ValueError(t("maven.snapshot_versioning_missing"))

    normalized_classifier = _normalize_classifier(classifier)
    snapshot_versions = versioning.findall("snapshotVersions/snapshotVersion")

    for snapshot_version in snapshot_versions:
        extension = snapshot_version.findtext("extension")
        snapshot_classifier = _normalize_classifier(
            snapshot_version.findtext("classifier")
        )
        value = snapshot_version.findtext("value")

        if (
            extension == "jar"
            and snapshot_classifier == normalized_classifier
            and value
        ):
            return value.strip()

    if normalized_classifier is not None and snapshot_versions:
        raise ValueError(
            t("maven.snapshot_classifier_missing", classifier=normalized_classifier)
        )

    base_version = metadata.findtext("version")
    timestamp = versioning.findtext("snapshot/timestamp")
    build_number = versioning.findtext("snapshot/buildNumber")

    if base_version and timestamp and build_number:
        prefix = base_version.removesuffix("-SNAPSHOT")
        return f"{prefix}-{timestamp.strip()}-{build_number.strip()}"

    raise ValueError(t("maven.snapshot_version_missing"))


def _build_artifact_url(core: Maven, version: str, resolved_version: str) -> str:
    group_id, artifact_id, repo_url = _require_maven_coordinates(core)
    group_path = group_id.replace(".", "/")
    repo_url = repo_url.rstrip("/")
    normalized_classifier = _normalize_classifier(core.classifier)
    classifier_suffix = f"-{normalized_classifier}" if normalized_classifier else ""

    return (
        f"{repo_url}/{group_path}/{artifact_id}/{version}/"
        f"{artifact_id}-{resolved_version}{classifier_suffix}.jar"
    )


def _normalize_classifier(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


def _require_maven_coordinates(core: Maven) -> tuple[str, str, str]:
    if not core.group_id:
        raise ValueError(t("maven.group_id_missing", core_id=core.id))

    if not core.artifact_id:
        raise ValueError(t("maven.artifact_id_missing", core_id=core.id))

    if not core.url:
        raise ValueError(t("maven.url_missing", core_id=core.id))

    return core.group_id, core.artifact_id, core.url
