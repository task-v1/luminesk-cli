from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CoreDownloadInfo:
    url: str
    hash: str
