from __future__ import annotations

from luminesk.core.base import JavaCore
from luminesk.models.registry import GitHubRelease


class AllayCore(JavaCore):
    id = "allay"
    name = "Allay"
    description = {
        "en": "Next-generation Minecraft: Bedrock Edition server software aims to be reliable, fast and feature-rich.",
        "ru": "Ядро следующего поколения для Minecraft Bedrock Edition, надежное, быстрое и многофункциональное.",
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
