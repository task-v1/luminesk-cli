from __future__ import annotations

from typing import ClassVar

from luminesk.core.base import BaseCore
from luminesk.cores import ALL_CORES


class CoreRegistry:
    _cores: ClassVar[dict[str, BaseCore] | None] = None

    @classmethod
    def get_all(cls) -> list[BaseCore]:
        return list(cls._load_cores().values())

    @classmethod
    def get_by_id(cls, core_id: str) -> BaseCore | None:
        return cls._load_cores().get(core_id.strip().lower())

    @classmethod
    def _load_cores(cls) -> dict[str, BaseCore]:
        if cls._cores is None:
            cls._cores = {}
            for core_cls in ALL_CORES:
                core_instance = core_cls()  # type: ignore[abstract]
                cls._cores[core_instance.id.strip().lower()] = core_instance

        return cls._cores


registry = CoreRegistry()
