from __future__ import annotations

import abc
from pathlib import Path

from rich.console import Console

from luminesk.models.manager import DownloadedCore
from luminesk.models.registry import CoreProvider


class BaseCore(abc.ABC):
    id: str
    name: str
    description: dict[str, str]
    required_setup: bool = False
    dont_create_config: bool = False
    config_file: str = "server.properties"
    port_way: str = "server-port"
    logo: str | None = None
    url: str = ""
    _provider: CoreProvider | None = None

    @property
    def localized_description(self) -> str:
        from luminesk.core.messages import DEFAULT_LANGUAGE, _current_language

        lang = _current_language

        if lang in self.description:
            return self.description[lang]

        return self.description.get(DEFAULT_LANGUAGE, "")

    def download(
        self,
        target_directory: Path,
        console: Console | None = None,
        skip_if_hash: str | None = None,
    ) -> DownloadedCore | None:
        if self._provider is None:
            from luminesk.core.messages import t

            raise NotImplementedError(t("core.download_not_supported"))

        from luminesk.core.manager import download_core_raw

        return download_core_raw(
            self._provider, target_directory, console, skip_if_hash
        )

    def get_availability_check_url(self) -> str:
        if self._provider is None:
            from luminesk.core.messages import t

            raise NotImplementedError(t("core.diagnostics_not_supported"))

        return self._provider.get_availability_check_url()

    @abc.abstractmethod
    def get_docker_image(self) -> str:
        pass

    @abc.abstractmethod
    def get_run_command(self, executable_name: str) -> str:
        pass

    def resolve_image(self, tag_or_image: str | None) -> str:
        if not tag_or_image:
            return self.get_docker_image()

        return tag_or_image


class JavaCore(BaseCore, abc.ABC):
    default_java_version: str = "21"

    def get_docker_image(self) -> str:
        return f"eclipse-temurin:{self.default_java_version}-jre"

    def get_run_command(self, executable_name: str) -> str:
        return f"java -jar {executable_name}"


class PhpCore(BaseCore, abc.ABC):
    def get_docker_image(self) -> str:
        return "ghcr.io/pmmp/pocketmine-mp:latest"

    def get_run_command(self, executable_name: str) -> str:
        return f"php {executable_name}"


class GoCore(BaseCore, abc.ABC):
    def get_docker_image(self) -> str:
        return "golang:1.26-alpine"

    def get_run_command(self, executable_name: str) -> str:
        return f"./{executable_name}"


class RustCore(BaseCore, abc.ABC):
    def get_docker_image(self) -> str:
        return "debian:bookworm-slim"

    def get_run_command(self, executable_name: str) -> str:
        return f"./{executable_name}"


class NodeCore(BaseCore, abc.ABC):
    def get_docker_image(self) -> str:
        return "node:20-alpine"

    def get_run_command(self, executable_name: str) -> str:
        return f"node {executable_name}"


class PythonCore(BaseCore, abc.ABC):
    def get_docker_image(self) -> str:
        return "python:3.13-alpine"

    def get_run_command(self, executable_name: str) -> str:
        return f"python {executable_name}"
