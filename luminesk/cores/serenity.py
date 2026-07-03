from __future__ import annotations

import os
import tarfile
from pathlib import Path

from rich.console import Console

from luminesk.core.base import RustCore
from luminesk.models.manager import DownloadedCore
from luminesk.utils.downloads import download_url


class SerenityCore(RustCore):
    id = "serenity"
    name = "Serenity"
    description = {
        "en": "A high-performance Minecraft: Bedrock Edition server software written in TypeScript.",
        "ru": "Высокопроизводительное серверное ПО для Minecraft: Bedrock Edition, написанное на TypeScript.",
        "uk": "Високопродуктивне серверне ПЗ для Minecraft: Bedrock Edition, написане на TypeScript.",
        "ja": "TypeScript で開発された高性能な Minecraft: Bedrock Edition 向けサーバーソフトウェア。",
        "zh": "使用 TypeScript 编写的高性能 Minecraft: Bedrock Edition 服务器软件。",
    }
    url = "https://github.com/SerenityJS/serenity"
    config_file = "server.properties"
    port_way = "server-port"

    def download(
        self,
        target_directory: Path,
        console: Console | None = None,
        skip_if_hash: str | None = None,
    ) -> DownloadedCore | None:
        import httpx

        from luminesk.utils.github_releases import get_release_asset_info

        computed_hash = "latest"
        download_link = None

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                download_link, computed_hash = get_release_asset_info(
                    client, self.url, "*ubuntu*.tar.gz", tag="latest"
                )
        except Exception:
            pass

        if not download_link:
            from luminesk.core.messages import t

            raise RuntimeError(t("core.serenity.asset_not_found"))

        # Check if already installed and can skip
        binary_name = "serenity"
        binary_path = None

        for p in target_directory.rglob("serenityjs-*"):
            if p.is_file():
                binary_path = p
                binary_name = str(p.relative_to(target_directory))
                break

        if (
            skip_if_hash is not None
            and skip_if_hash == computed_hash
            and binary_path is not None
        ):
            return None

        tar_path = target_directory / "serenity.tar.gz"
        download_url(download_link, tar_path, console=console)

        # Extract tarball
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=target_directory)

        # Remove tarball
        try:
            tar_path.unlink()
        except OSError:
            pass

        # Identify the extracted binary name
        for p in target_directory.rglob("serenityjs-*"):
            if p.is_file():
                binary_name = str(p.relative_to(target_directory))

                try:
                    os.chmod(p, 0o755)
                except OSError:
                    pass

                break

        return DownloadedCore(
            executable_path=target_directory / binary_name, hash=computed_hash
        )
