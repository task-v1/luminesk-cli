from __future__ import annotations

from luminesk.core.base import JavaCore
from luminesk.models.registry import GitHubRelease


class PowerNukkitXCore(JavaCore):
    id = "pnx"
    name = "PowerNukkitX"
    required_setup = True
    description = {
        "en": "Advanced core with support for newer blocks and entities.",
        "ru": "Улучшенное ядро с поддержкой новых блоков и сущностей.",
        "uk": "Покращені блоки та сутності у ядрі.",
        "ja": "新しいブロックとエンティティをサポートする高度なコア。",
        "zh": "支持新方块和实体的先进核心。",
    }
    url = "https://github.com/PowerNukkitX/PowerNukkitX"
    config_file = "pnx.yml"
    port_way = "settings.port"

    _provider = GitHubRelease(
        id="pnx",
        name="PowerNukkitX",
        description=description,
        url=url,
        config_file=config_file,
        port_way=port_way,
        release_file="powernukkitx.jar",
    )
