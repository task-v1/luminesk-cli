from __future__ import annotations

from luminesk_cli.core.base import PhpCore
from luminesk_cli.models.registry import GitHubRelease


class BetterAltayCore(PhpCore):
    id = "better-altay"
    name = "BetterAltay"
    required_setup = True
    description = {
        "en": "A feature-rich, optimized PHP server software for Minecraft: Bedrock Edition, based on Altay/PocketMine-MP.",
        "ru": "Многофункциональное оптимизированное серверное ПО на PHP для Minecraft: Bedrock Edition, основанное на Altay/PocketMine-MP.",
        "uk": "Багатофункціональне оптимізоване серверне ПЗ на PHP для Minecraft: Bedrock Edition, засноване на Altay/PocketMine-MP.",
        "ja": "Altay/PocketMine-MP をベースとした、多機能で最適化された Minecraft: Bedrock Edition 向け PHP サーバーソフトウェア。",
        "zh": "基于 Altay/PocketMine-MP 的功能丰富且经过优化的 Minecraft: Bedrock Edition PHP 服务器软件。",
    }
    url = "https://github.com/Benedikt05/BetterAltay"
    config_file = "server.properties"
    port_way = "server-port"

    _provider = GitHubRelease(
        id="better-altay",
        name="BetterAltay",
        description=description,
        url=url,
        config_file=config_file,
        port_way=port_way,
        release_file="BetterAltay.phar",
    )

    def get_run_command(self, executable_name: str) -> str:
        return f"php {executable_name} --no-wizard"

    def get_docker_image(self) -> str:
        return "ghcr.io/pmmp/pocketmine-mp:4"
