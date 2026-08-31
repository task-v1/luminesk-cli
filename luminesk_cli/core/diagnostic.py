from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

from luminesk_cli.core.messages import t
from luminesk_cli.core.registry import registry
from luminesk_cli.models.registry import CoreProvider
from luminesk_cli.utils.errors import format_error
from luminesk_cli.utils.http import request_with_retries

REPOSITORY_CHECK_TIMEOUT = 10.0
MAX_REPOSITORY_CHECK_WORKERS = 4


@dataclass
class DiagnosticResult:
    name: str
    status: bool
    message: str


def check_repositories() -> list[DiagnosticResult]:
    cores = [
        core
        for core in registry.get_all()
        if getattr(core, "_provider", None) is not None
    ]

    if not cores:
        return []

    max_workers = min(MAX_REPOSITORY_CHECK_WORKERS, len(cores))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_check_repository, cores))


def _check_repository(core: CoreProvider) -> DiagnosticResult:
    try:
        check_url = core.get_availability_check_url()
        with httpx.Client(
            timeout=REPOSITORY_CHECK_TIMEOUT, follow_redirects=True
        ) as client:
            return _check_source(client, core.name, check_url)
    except Exception as exc:
        return DiagnosticResult(
            name=t("diagnostic.source_name", core_name=core.name),
            status=False,
            message=t("common.error_prefix", error=format_error(exc)),
        )


def _check_source(
    client: httpx.Client, core_name: str, check_url: str
) -> DiagnosticResult:
    try:
        response = request_with_retries(
            client,
            "HEAD",
            check_url,
            retry_on_status=True,
        )
        if response.status_code == 405:
            response = request_with_retries(
                client,
                "GET",
                check_url,
                retry_on_status=True,
            )

        if response.is_success:
            return DiagnosticResult(
                name=t("diagnostic.source_name", core_name=core_name),
                status=True,
                message=t("diagnostic.source_ok"),
            )

        return DiagnosticResult(
            name=t("diagnostic.source_name", core_name=core_name),
            status=False,
            message=t(
                "diagnostic.source_http_status", status_code=response.status_code
            ),
        )
    except Exception as exc:
        return DiagnosticResult(
            name=t("diagnostic.source_name", core_name=core_name),
            status=False,
            message=t("common.error_prefix", error=format_error(exc)),
        )
