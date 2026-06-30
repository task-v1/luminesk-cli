from __future__ import annotations

from luminesk.core.base import PhpCore
from luminesk.models.registry import GitHubRelease


class BetterAltayCore(PhpCore):
    id = "better-altay"
    name = "BetterAltay"
    required_setup = True
    description = {
        "en": "A feature-rich optimized PHP server software for Minecraft: Bedrock Edition, a fork of Altay/PocketMine-MP.",
        "ru": "Многофункциональное оптимизированное PHP-ядро для Minecraft Bedrock Edition, форк Altay/PocketMine-MP.",
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
