"""Source resolver protocol and lazy built-in registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import SourceSpec


@dataclass(slots=True, frozen=True)
class Resolution:
    provider: str
    version: str
    source_revision: str
    url: str
    target: str
    size: int | None = None
    digest: str | None = None
    media_type: str | None = None


class SourceResolver(Protocol):
    def resolve(self, source: SourceSpec, client: httpx.Client) -> Resolution: ...


class ResolverRegistry:
    def __init__(self) -> None:
        self._resolvers: dict[str, SourceResolver] = {}

    def register(self, provider: str, resolver: SourceResolver) -> None:
        self._resolvers[provider] = resolver

    def resolve(
        self,
        source: SourceSpec,
        client: httpx.Client,
    ) -> Resolution:
        resolver = self._resolvers.get(source.provider)

        if resolver is None:
            raise ResolutionError(f"no resolver registered for {source.provider}")

        return resolver.resolve(source, client)


def default_registry() -> ResolverRegistry:
    from luminesk_cli.infrastructure.sources.github_release import (
        GitHubReleaseResolver,
    )
    from luminesk_cli.infrastructure.sources.http import HttpResolver
    from luminesk_cli.infrastructure.sources.jenkins import JenkinsResolver
    from luminesk_cli.infrastructure.sources.maven import MavenResolver

    registry = ResolverRegistry()
    registry.register("github-release", GitHubReleaseResolver())
    registry.register("maven", MavenResolver())
    registry.register("jenkins", JenkinsResolver())
    registry.register("http", HttpResolver())
    return registry
