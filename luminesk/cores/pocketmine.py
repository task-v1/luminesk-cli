from __future__ import annotations

from luminesk.core.base import PhpCore
from luminesk.models.registry import GitHubRelease


class PocketMineCore(PhpCore):
    id = "pocketmine"
    name = "PocketMine-MP"
    required_setup = True
    description = {
        "en": "A highly customizable open-source server software for Minecraft: Bedrock Edition written in PHP.",
        "ru": "Высоконастраиваемое серверное ПО с открытым исходным кодом для Minecraft: Bedrock Edition, написанное на PHP.",
        "uk": "Високонастроюване серверне ПЗ з відкритим вихідним кодом для Minecraft: Bedrock Edition, написане на PHP.",
        "ja": "PHP で開発された、Minecraft: Bedrock Edition 向けの高いカスタマイズ性を持つオープンソースサーバーソフトウェア。",
        "zh": "使用 PHP 编写的高可定制开源 Minecraft: Bedrock Edition 服务器软件。",
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
