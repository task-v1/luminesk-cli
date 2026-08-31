from __future__ import annotations

from luminesk_cli.core.base import JavaCore
from luminesk_cli.models.registry import Jenkins


class NukkitMotCore(JavaCore):
    id = "nukkit-mot"
    name = "Nukkit-MOT"
    description = {
        "en": "Core with multi-version MCBE support and a strong vanilla focus.",
        "ru": "Ядро с поддержкой мультиверсионности MCBE и сильным уклоном в ванилу.",
        "uk": "Ядро з підтримкою мультиверсійності MCBE та сильним ухилом у ванілу.",
        "ja": "マルチバージョンのMCBEサポートとバニラへの強いフォーカスを持つコア。",
        "zh": "支持多版本 MCBE 且高度关注原版（Vanilla）的核心。",
    }
    url = "https://motci.cn/job/Nukkit-MOT/job/master"
    config_file = "server.properties"
    port_way = "server-port"

    _provider = Jenkins(
        id="nukkit-mot",
        name="Nukkit-MOT",
        description=description,
        url=url,
    )
