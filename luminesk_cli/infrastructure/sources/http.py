"""Direct HTTP artifact adapter; mutable URLs are pinned during fetch."""

from __future__ import annotations

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import SourceSpec
from luminesk_cli.infrastructure.security.network import validate_remote_url
from luminesk_cli.infrastructure.sources.base import Resolution


class HttpResolver:
    def resolve(self, source: SourceSpec, client: httpx.Client) -> Resolution:
        del client

        if source.url is None:
            raise ResolutionError("http source requires url")

        validate_remote_url(
            source.url,
            allow_http=source.allow_http,
            allow_private_network=source.allow_private_network,
        )
        version = source.version or "pinned"
        return Resolution(
            provider=source.provider,
            version=version,
            source_revision=version,
            url=source.url,
            target=source.target,
        )
