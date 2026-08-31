from __future__ import annotations

from luminesk_cli.core.base import JavaCore
from luminesk_cli.models.registry import Maven


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

    _provider = Maven(
        id="nukkit",
        name="Nukkit",
        description=description,
        url="https://repo.opencollab.dev/maven-snapshots",
        group_id="cn.nukkit",
        artifact_id="nukkit",
        is_snapshot=True,
        config_file=config_file,
        port_way=port_way,
    )
