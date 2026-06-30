from __future__ import annotations

from luminesk.core.base import PhpCore
from luminesk.models.registry import GitHubRelease


class LunacyCore(PhpCore):
    id = "lunacy"
    name = "Lunacy"
    required_setup = True
    description = {
        "en": "Server software for Minecraft Bedrock Edition, built on top of PocketMine-NetherGames."
    }
    url = "https://github.com/karepanov35/Lunacy"
    config_file = "server.properties"
    port_way = "server-port"

    _provider = GitHubRelease(
        id="lunacy",
        name="Lunacy",
        description=description,
        url=url,
        config_file=config_file,
        port_way=port_way,
        release_file="PocketMine-MP.phar",
    )

    def get_run_command(self, executable_name: str) -> str:
        return f"php {executable_name}"
