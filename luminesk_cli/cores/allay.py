from __future__ import annotations

from luminesk_cli.core.base import JavaCore
from luminesk_cli.models.registry import GitHubRelease


class AllayCore(JavaCore):
    id = "allay"
    name = "Allay"
    description = {
        "en": "Next-generation Minecraft: Bedrock Edition server software that aims to be reliable, fast, and feature-rich.",
        "ru": "Серверное ПО нового поколения для Minecraft: Bedrock Edition, которое отличается надежностью, высокой производительностью и богатым набором функций.",
        "uk": "Серверне ПЗ нового покоління для Minecraft: Bedrock Edition, яке вирізняється надійністю, високою продуктивністю та широким набором функцій.",
        "ja": "信頼性、高速性、豊富な機能を備えた次世代の Minecraft: Bedrock Edition サーバーソフトウェア。",
        "zh": "新一代 Minecraft: Bedrock Edition 服务器软件，旨在提供高可靠性、高性能和丰富的功能。",
    }
    url = "https://github.com/AllayMC/Allay"
    config_file = "server-settings.yml"
    port_way = "network-settings.port"

    _provider = GitHubRelease(
        id="allay",
        name="Allay",
        description=description,
        url=url,
        release_file="allay-server-*-shaded.jar",
    )
