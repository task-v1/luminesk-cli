from __future__ import annotations

from luminesk.core.base import JavaCore
from luminesk.models.registry import Maven


class LumiCore(JavaCore):
    id = "lumi"
    name = "Lumi"
    description = {
        "en": "Nukkit-MOT-based core focused on optimization and customization.",
        "ru": "Ядро на базе Nukkit-MOT, ориентированное на оптимизацию и кастомизацию.",
        "uk": "Ядро на базі Nukkit-MOT, орієнтоване на оптимізацію та кастомізацію.",
        "ja": "最適化とカスタマイズに焦点を当てたNukkit-MOTベース of コア。",
        "zh": "基于 Nukkit-MOT，专注于优化和自定义的核心。",
    }
    url = "https://repo.lumi.su/releases/"
    config_file = "settings.yml"
    port_way = "general.server-port"

    _provider = Maven(
        id="lumi",
        name="Lumi",
        description=description,
        url=url,
        group_id="com.koshakmine",
        artifact_id="Lumi",
        config_file=config_file,
        port_way=port_way,
    )
