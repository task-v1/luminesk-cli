"""Resolve a manifest into an exact, reproducible lockfile."""

from __future__ import annotations

from pathlib import Path

import httpx

from luminesk_cli.domain.errors import ResolutionError, SecurityError
from luminesk_cli.domain.lockfile import (
    BuildLock,
    Lockfile,
    RecipeLock,
    ResolvedSource,
    RuntimeLock,
)
from luminesk_cli.domain.manifest import Manifest, SourceSpec
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.dockerfile import resolve_build_images
from luminesk_cli.infrastructure.fetch import SecureFetcher
from luminesk_cli.infrastructure.oci import OciImageResolver
from luminesk_cli.infrastructure.platform import current_platform
from luminesk_cli.infrastructure.sources.base import ResolverRegistry, default_registry


class LockService:
    def __init__(
        self,
        cache: ContentCache,
        *,
        registry: ResolverRegistry | None = None,
        image_resolver: OciImageResolver | None = None,
        client: httpx.Client | None = None,
        fetcher: SecureFetcher | None = None,
    ) -> None:
        self.cache = cache
        self.registry = registry or default_registry()
        self.image_resolver = image_resolver or OciImageResolver()
        self.client = client
        self.fetcher = fetcher or SecureFetcher(cache, client=client)

    def create(
        self,
        manifest: Manifest,
        recipe_root: Path,
        *,
        recipe_source: str | None = None,
        recipe_revision: str | None = None,
        recipe_ref: str | None = None,
        recipe_tracking: bool = False,
        target: str | None = None,
    ) -> Lockfile:
        target_platform = target or current_platform()

        if manifest.package.platforms and target_platform not in manifest.package.platforms:
            raise ResolutionError(
                f"recipe does not support target {target_platform}",
                target=target_platform,
            )

        owned_client = self.client is None
        client = self.client or httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
        )

        try:
            sources = {
                source.id: self._resolve_source(source, recipe_root, client)
                for source in manifest.sources
                if not source.platforms or target_platform in source.platforms
            }
        finally:
            if owned_client:
                client.close()

        recipe = None

        if recipe_source is not None or recipe_revision is not None:
            if not recipe_source or not recipe_revision:
                raise ResolutionError(
                    "recipe source and revision must be provided together"
                )

            recipe = RecipeLock(
                source=recipe_source,
                revision=recipe_revision,
                ref=recipe_ref,
                tracking=recipe_tracking,
            )

        return Lockfile(
            manifest_digest=manifest.digest,
            target=target_platform,
            sources=sources,
            runtime=RuntimeLock(image=self.image_resolver.resolve(manifest.runtime.image)),
            build=(
                BuildLock(
                    images=resolve_build_images(
                        recipe_root,
                        manifest.build,
                        self.image_resolver,
                    )
                )
                if manifest.build is not None
                else None
            ),
            recipe=recipe,
        )

    def _resolve_source(
        self,
        source: SourceSpec,
        recipe_root: Path,
        client: httpx.Client,
    ) -> ResolvedSource:
        if source.provider == "local-file":
            return self._resolve_local(source, recipe_root)

        resolution = self.registry.resolve(source, client)
        blob = self.fetcher.fetch(
            resolution.url,
            max_size=source.max_size,
            expected_digest=resolution.digest,
            expected_size=resolution.size,
            allow_http=source.allow_http,
            allow_private_network=source.allow_private_network,
        )

        return ResolvedSource(
            provider=source.provider,
            version=resolution.version,
            source_revision=resolution.source_revision,
            url=resolution.url,
            size=blob.size,
            digest=blob.digest,
            target=source.target,
            media_type=resolution.media_type,
        )

    def _resolve_local(
        self,
        source: SourceSpec,
        recipe_root: Path,
    ) -> ResolvedSource:
        if source.path is None:
            raise ResolutionError("local-file source requires path")

        root = recipe_root.resolve()
        candidate = (root / source.path).resolve()

        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise SecurityError(
                "local source must be a regular file inside the recipe root",
                path=str(candidate),
            )

        if candidate.stat().st_size > source.max_size:
            raise SecurityError(
                "local source exceeds configured size limit",
                size=candidate.stat().st_size,
                limit=source.max_size,
            )

        from luminesk_cli.infrastructure.cache import digest_file

        digest, _ = digest_file(candidate)
        blob = self.cache.store(candidate, digest)
        return ResolvedSource(
            provider=source.provider,
            version=source.version or "local",
            source_revision=digest,
            url=f"local:{source.path}",
            size=blob.size,
            digest=blob.digest,
            target=source.target,
        )
