from typing import Any

import httpx

from luminesk_cli.core.messages import t
from luminesk_cli.models.registry import Jenkins
from luminesk_cli.utils.download_models import CoreDownloadInfo
from luminesk_cli.utils.errors import format_error
from luminesk_cli.utils.http import get_json_object_with_retries


def get_build_info_url(core: Jenkins) -> str:
    job_url = _require_jenkins_job_url(core).rstrip("/")
    return f"{job_url}/lastSuccessfulBuild/api/json"


def get_latest_download_url(core: Jenkins, client: httpx.Client | None = None) -> str:
    return get_latest_download_info(core, client=client).url


def get_latest_download_info(
    core: Jenkins, client: httpx.Client | None = None
) -> CoreDownloadInfo:
    if client is not None:
        return _get_latest_download_info(client, core)

    with httpx.Client(timeout=10.0, follow_redirects=True) as owned_client:
        return _get_latest_download_info(owned_client, core)


def _get_latest_download_info(client: httpx.Client, core: Jenkins) -> CoreDownloadInfo:
    job_url = _require_jenkins_job_url(core).rstrip("/")
    build_info = _fetch_json(client, get_build_info_url(core))
    artifacts = build_info.get("artifacts")

    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError(t("jenkins.artifacts_missing", core_id=core.id))

    artifact = _select_jenkins_artifact(artifacts, getattr(core, "classifier", None))

    commit_sha = None

    for action in build_info.get("actions", []):
        if not isinstance(action, dict):
            continue
        last_built = action.get("lastBuiltRevision")
        if isinstance(last_built, dict):
            sha = last_built.get("SHA1")

            if isinstance(sha, str) and sha.strip():
                commit_sha = sha.strip().lower()
                break

    if not commit_sha:
        import hashlib
        build_version = _get_build_version(build_info)
        commit_sha = hashlib.sha1(build_version.encode()).hexdigest()

    return CoreDownloadInfo(
        url=f"{job_url}/lastSuccessfulBuild/artifact/{artifact}",
        hash=commit_sha,
    )


def _fetch_json(client: httpx.Client, url: str) -> dict[str, Any]:
    try:
        return get_json_object_with_retries(client, url)
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            t("jenkins.fetch_json_http", url=url, status_code=exc.response.status_code)
        ) from exc
    except httpx.RequestError as exc:
        raise ValueError(
            t("jenkins.fetch_json_error", url=url, error=format_error(exc))
        ) from exc
    except ValueError as exc:
        raise ValueError(t("jenkins.invalid_json", url=url)) from exc


def _select_jenkins_artifact(artifacts: list[Any], classifier: str | None) -> str:
    normalized_classifier = _normalize_classifier(classifier)
    candidates: list[tuple[str, str]] = []

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue

        relative_path = artifact.get("relativePath")
        file_name = artifact.get("fileName")

        if not isinstance(relative_path, str) or not isinstance(file_name, str):
            continue

        if not file_name.endswith(".jar"):
            continue

        candidates.append((file_name, relative_path))

    if not candidates:
        raise ValueError(t("jenkins.no_jar_artifacts"))

    if normalized_classifier is not None:
        suffix = f"-{normalized_classifier}.jar"
        for file_name, relative_path in candidates:
            if file_name.endswith(suffix):
                return relative_path
        raise ValueError(
            t("jenkins.classifier_missing", classifier=normalized_classifier)
        )

    for file_name, relative_path in candidates:
        if not _has_auxiliary_jar_suffix(file_name):
            return relative_path

    raise ValueError(t("jenkins.primary_jar_missing"))


def _get_build_version(build_info: dict[str, Any]) -> str:
    number = build_info.get("number")

    if isinstance(number, int):
        return f"build-{number}"

    for key in ("id", "displayName"):
        value = build_info.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return "latest"


def _normalize_classifier(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


def _has_auxiliary_jar_suffix(file_name: str) -> bool:
    auxiliary_suffixes = ("-sources.jar", "-javadoc.jar", "-tests.jar")
    return file_name.endswith(auxiliary_suffixes)


def _require_jenkins_job_url(core: Jenkins) -> str:
    if not core.url:
        raise ValueError(t("jenkins.url_missing", core_id=core.id))

    return core.url
