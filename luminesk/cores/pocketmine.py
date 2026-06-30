from __future__ import annotations

from luminesk.core.base import PhpCore
from luminesk.models.registry import GitHubRelease


class PocketMineCore(PhpCore):
    id = "pocketmine"
    name = "PocketMine-MP"
    required_setup = True
    description = {
        "en": "A highly customizable open-source server software for Minecraft: Bedrock Edition written in PHP.",
        "ru": "Высокопроизводительное ядро для Minecraft Bedrock Edition с открытым исходным кодом на PHP.",
    }
    url = "https://github.com/pmmp/PocketMine-MP"
    config_file = "server.properties"
    port_way = "server-port"

    _provider = GitHubRelease(
        id="pocketmine",
        name="PocketMine-MP",
        description=description,
        url=url,
        config_file=config_file,
        port_way=port_way,
        release_file="PocketMine-MP.phar",
    )

    def get_run_command(self, executable_name: str) -> str:
        return f"php {executable_name}"
