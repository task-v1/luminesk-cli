from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class CoreProvider:
    id: str
    name: str
    description: dict[str, str]
    url: str
    config_file: str = "server.properties"
    port_way: str = "server-port"
    logo: str | None = None

    @property
    def localized_description(self) -> str:
        from luminesk_cli.core.messages import DEFAULT_LANGUAGE, _current_language

        lang = _current_language

        if lang in self.description:
            return self.description[lang]

        return self.description.get(DEFAULT_LANGUAGE, "")

    def get_availability_check_url(self) -> str:
        from luminesk_cli.utils.downloads import get_availability_check_url

        return get_availability_check_url(self)

    def get_latest_download_url(self) -> str:
        from luminesk_cli.utils.downloads import get_latest_download_url

        return get_latest_download_url(self)


@dataclass(frozen=True, kw_only=True)
class Maven(CoreProvider):
    group_id: str
    artifact_id: str
    classifier: str | None = None
    is_snapshot: bool = False


@dataclass(frozen=True, kw_only=True)
class Jenkins(CoreProvider):
    classifier: str | None = None


@dataclass(frozen=True, kw_only=True)
class GitHubRelease(CoreProvider):
    release_file: str

