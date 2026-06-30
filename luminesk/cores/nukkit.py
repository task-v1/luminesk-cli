from __future__ import annotations

from pathlib import Path

import httpx
from rich.console import Console

from luminesk.core.base import JavaCore
from luminesk.models.manager import DownloadedCore
from luminesk.models.registry import CoreProvider
from luminesk.utils.downloads import download_url


class NukkitCore(JavaCore):
    id = "nukkit"
    name = "Nukkit"
    description = {
        "en": "Original Minecraft server core.",
        "ru": "Оригинальное ядро сервера Minecraft.",
        "uk": "Оригінальне ядро сервера Minecraft.",
        "ja": "オリジナルのMinecraftサーバーコア。",
        "zh": "原版 Minecraft 服务器核心。",
    }
    url = "https://dl.opencollab.dev/nukkit"
    config_file = "server.properties"
    port_way = "server-port"
    required_setup = True

    _provider = CoreProvider(
        id="nukkit",
        name="Nukkit",
        description=description,
        url=url,
        config_file=config_file,
        port_way=port_way,
    )

    def get_availability_check_url(self) -> str:
        return "https://repo.opencollab.dev/api/maven/latest/file/maven-snapshots/cn/nukkit/nukkit/1.0-SNAPSHOT?extension=jar"

    def download(
        self,
        target_directory: Path,
        console: Console | None = None,
        skip_if_hash: str | None = None,
    ) -> DownloadedCore | None:
        sha1_url = "https://repo.opencollab.dev/api/maven/latest/file/maven-snapshots/cn/nukkit/nukkit/1.0-SNAPSHOT?extension=jar.sha1"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(sha1_url)
                resp.raise_for_status()
                sha1 = resp.text.strip().split()[0].lower()
        except Exception as exc:
            from luminesk.core.messages import t
            raise RuntimeError(t("maven.fetch_xml_error", url=sha1_url, error=str(exc)))

        target_path = target_directory / "nukkit.jar"

        if skip_if_hash is not None and skip_if_hash == sha1 and target_path.is_file():
            return None

        download_link = "https://repo.opencollab.dev/api/maven/latest/file/maven-snapshots/cn/nukkit/nukkit/1.0-SNAPSHOT?extension=jar"
        download_url(download_link, target_path, console=console)

        return DownloadedCore(executable_path=target_path, hash=sha1)
