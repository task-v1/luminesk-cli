"""Jenkins artifact source adapter."""

from __future__ import annotations

import fnmatch
from typing import Any

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import JenkinsOptions, SourceSpec
from luminesk_cli.domain.primitives import safe_relative_path
from luminesk_cli.infrastructure.sources.base import Resolution
from luminesk_cli.infrastructure.sources.common import request_json_object


class JenkinsResolver:
    def resolve(self, source: SourceSpec, client: httpx.Client) -> Resolution:
        if not isinstance(source.options, JenkinsOptions):
            raise ResolutionError("jenkins source has invalid options")

        options = source.options
        job_url = f"{options.base_url.rstrip('/')}/job/{options.job.strip('/')}"
        build_selector = str(options.build)
        build_url = f"{job_url}/{build_selector}"
        metadata = request_json_object(client, f"{build_url}/api/json", source)
        artifact = _select_artifact(metadata.get("artifacts"), options.artifact)
        build_number = metadata.get("number")
        revision = _source_revision(metadata, build_number)
        version = str(build_number) if isinstance(build_number, int) else revision
        relative_path = safe_relative_path(
            artifact["relativePath"], "jenkins.artifact.relativePath"
        )

        return Resolution(
            type=source.type,
            version=version,
            source_revision=revision,
            url=f"{build_url}/artifact/{relative_path}",
            target=source.target,
            size=(
                artifact["fileSize"]
                if isinstance(artifact.get("fileSize"), int)
                else None
            ),
            media_type="application/java-archive"
            if relative_path.endswith(".jar")
            else None,
        )


def _select_artifact(artifacts: Any, pattern: str) -> dict[str, Any]:
    if not isinstance(artifacts, list):
        raise ResolutionError("Jenkins artifacts must be an array")

    matches = []

    for item in artifacts:
        if not isinstance(item, dict):
            continue

        relative_path = item.get("relativePath")
        file_name = item.get("fileName")

        if not isinstance(relative_path, str) or not isinstance(file_name, str):
            continue

        if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(
            relative_path, pattern
        ):
            matches.append(item)

    if not matches:
        raise ResolutionError(f"no Jenkins artifact matches {pattern}")

    if len(matches) != 1:
        raise ResolutionError(
            f"Jenkins artifact pattern {pattern} is ambiguous", count=len(matches)
        )

    return matches[0]


def _source_revision(metadata: dict[str, Any], build_number: Any) -> str:
    actions = metadata.get("actions", [])

    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue

            revision = action.get("lastBuiltRevision")

            if isinstance(revision, dict):
                sha = revision.get("SHA1")

                if isinstance(sha, str) and sha.strip():
                    return sha.strip().lower()

    if isinstance(build_number, int):
        return f"build-{build_number}"

    raise ResolutionError("Jenkins metadata contains no immutable revision")
