"""Maven repository source adapter with snapshot resolution."""

from __future__ import annotations

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import MavenOptions, SourceSpec
from luminesk_cli.infrastructure.sources.base import Resolution
from luminesk_cli.infrastructure.sources.common import (
    request_metadata,
    select_highest_version,
)


class MavenResolver:
    def resolve(self, source: SourceSpec, client: httpx.Client) -> Resolution:
        if not isinstance(source.options, MavenOptions):
            raise ResolutionError("maven source has invalid options")

        options = source.options
        metadata_url = _metadata_url(source)
        metadata = _parse_xml(
            request_metadata(client, metadata_url, source).content,
            metadata_url,
        )
        version = _select_version(metadata, options.version, options.channel)
        resolved_version = version

        if version.endswith("-SNAPSHOT"):
            version_url = _version_metadata_url(source, version)
            version_metadata = _parse_xml(
                request_metadata(client, version_url, source).content,
                version_url,
            )
            resolved_version = _snapshot_version(
                version_metadata,
                options.extension,
                options.classifier,
            )

        artifact_url = _artifact_url(source, version, resolved_version)
        digest = _optional_sha256(client, artifact_url, source)

        return Resolution(
            type=source.type,
            version=version,
            source_revision=resolved_version,
            url=artifact_url,
            target=source.target,
            digest=digest,
            media_type="application/java-archive"
            if options.extension == "jar"
            else None,
        )


def _group_path(source: SourceSpec) -> str:
    assert isinstance(source.options, MavenOptions)
    return source.options.group.replace(".", "/")


def _metadata_url(source: SourceSpec) -> str:
    assert isinstance(source.options, MavenOptions)
    options = source.options
    return (
        f"{options.repository.rstrip('/')}/{_group_path(source)}/"
        f"{options.artifact}/maven-metadata.xml"
    )


def _version_metadata_url(source: SourceSpec, version: str) -> str:
    return f"{_metadata_url(source).removesuffix('maven-metadata.xml')}{version}/maven-metadata.xml"


def _artifact_url(source: SourceSpec, version: str, resolved_version: str) -> str:
    assert isinstance(source.options, MavenOptions)
    options = source.options
    classifier = f"-{options.classifier}" if options.classifier else ""
    return (
        f"{options.repository.rstrip('/')}/{_group_path(source)}/"
        f"{options.artifact}/{version}/{options.artifact}-{resolved_version}"
        f"{classifier}.{options.extension}"
    )


def _parse_xml(content: bytes, url: str) -> Element:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ResolutionError("invalid Maven metadata XML", url=url) from exc

    for node in root.iter():
        if isinstance(node.tag, str) and "}" in node.tag:
            node.tag = node.tag.rsplit("}", 1)[-1]

    return root


def _select_version(metadata: Element, constraint: str, channel: str) -> str:
    versions = [
        node.text.strip()
        for node in metadata.findall("versioning/versions/version")
        if node.text and node.text.strip()
    ]

    if not versions:
        for key in ("release", "latest"):
            value = metadata.findtext(f"versioning/{key}")

            if value and value.strip():
                versions.append(value.strip())

    if not versions:
        raise ResolutionError("Maven metadata contains no versions")

    if constraint.endswith("-SNAPSHOT") and constraint in versions:
        return constraint

    return select_highest_version(versions, constraint, channel)


def _snapshot_version(
    metadata: Element,
    packaging: str,
    classifier: str | None,
) -> str:
    normalized_classifier = classifier or None

    for node in metadata.findall("versioning/snapshotVersions/snapshotVersion"):
        extension = node.findtext("extension")
        item_classifier = node.findtext("classifier") or None
        value = node.findtext("value")

        if (
            extension == packaging
            and item_classifier == normalized_classifier
            and value
        ):
            return value.strip()

    base_version = metadata.findtext("version")
    timestamp = metadata.findtext("versioning/snapshot/timestamp")
    build_number = metadata.findtext("versioning/snapshot/buildNumber")

    if base_version and timestamp and build_number:
        return (
            f"{base_version.removesuffix('-SNAPSHOT')}-"
            f"{timestamp.strip()}-{build_number.strip()}"
        )

    raise ResolutionError("Maven snapshot metadata has no matching artifact")


def _optional_sha256(
    client: httpx.Client,
    artifact_url: str,
    source: SourceSpec,
) -> str | None:
    try:
        response = request_metadata(client, f"{artifact_url}.sha256", source)
    except Exception:
        return None

    value = response.text.strip().split()[0].lower()

    if len(value) == 64 and all(character in "0123456789abcdef" for character in value):
        return f"sha256:{value}"

    return None
