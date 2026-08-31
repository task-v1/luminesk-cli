"""Direct HTTP artifact adapter; mutable URLs are pinned during fetch."""

from __future__ import annotations

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import HttpOptions, SourceSpec
from luminesk_cli.infrastructure.security.network import validate_remote_url
from luminesk_cli.infrastructure.sources.base import Resolution


class HttpResolver:
    def resolve(self, source: SourceSpec, client: httpx.Client) -> Resolution:
        del client

        if not isinstance(source.options, HttpOptions):
            raise ResolutionError("http source has invalid options")

        validate_remote_url(
            source.options.url,
            allow_http=source.allow_http,
            allow_private_network=source.allow_private_network,
        )
        version = source.options.version
        return Resolution(
            type=source.type,
            version=version,
            source_revision=version,
            url=source.options.url,
            target=source.target,
        )
