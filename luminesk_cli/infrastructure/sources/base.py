"""Source resolver protocol and lazy built-in registry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import httpx

from luminesk_cli.domain.errors import ResolutionError
from luminesk_cli.domain.manifest import SourceSpec


@dataclass(slots=True, frozen=True)
class Resolution:
    type: str
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
    def __init__(self, resolvers: Mapping[str, SourceResolver]) -> None:
        """Create an internal registry from built-ins or explicit test fakes."""

        self._resolvers = dict(resolvers)

    def resolve(
        self,
        source: SourceSpec,
        client: httpx.Client,
    ) -> Resolution:
        resolver = self._resolvers.get(source.type)

        if resolver is None:
            raise ResolutionError(f"no built-in resolver for {source.type}")

        return resolver.resolve(source, client)


def default_registry() -> ResolverRegistry:
    from luminesk_cli.infrastructure.sources.github_release import (
        GitHubReleaseResolver,
    )
    from luminesk_cli.infrastructure.sources.github_source import GitHubSourceResolver
    from luminesk_cli.infrastructure.sources.gitlab_job_artifact import (
        GitLabJobArtifactResolver,
    )
    from luminesk_cli.infrastructure.sources.gitlab_release import GitLabReleaseResolver
    from luminesk_cli.infrastructure.sources.http import HttpResolver
    from luminesk_cli.infrastructure.sources.jenkins import JenkinsResolver
    from luminesk_cli.infrastructure.sources.maven import MavenResolver
    from luminesk_cli.infrastructure.sources.mojang import MojangVersionResolver
    from luminesk_cli.infrastructure.sources.paper import PaperResolver

    return ResolverRegistry(
        {
            "github-release": GitHubReleaseResolver(),
            "maven": MavenResolver(),
            "jenkins": JenkinsResolver(),
            "http": HttpResolver(),
            "github-source": GitHubSourceResolver(),
            "gitlab-release": GitLabReleaseResolver(),
            "gitlab-job-artifact": GitLabJobArtifactResolver(),
            "mojang-version": MojangVersionResolver(),
            "paper": PaperResolver(),
        }
    )
