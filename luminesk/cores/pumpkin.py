from __future__ import annotations

import os
import platform
from pathlib import Path

from rich.console import Console

from luminesk.core.base import RustCore
from luminesk.models.manager import DownloadedCore
from luminesk.utils.downloads import download_url


class PumpkinCore(RustCore):
    id = "pumpkin"
    name = "Pumpkin"
    description = {
        "en": "A Minecraft server built entirely in Rust, offering a fast, efficient, and customizable experience.",
        "ru": "Высокопроизводительное серверное ядро для Minecraft, полностью написанное на Rust.",
        "uk": "Високопродуктивне серверне ядро для Minecraft, повністю написане на Rust.",
        "ja": "Rust で完全に開発された、高速で効率的かつカスタマイズ可能な Minecraft サーバーソフトウェア。",
        "zh": "完全使用 Rust 构建的 Minecraft 服务器，提供高速、高效且可定制的体验。",
    }
    url = "https://github.com/Pumpkin-MC/Pumpkin"
    config_file = "pumpkin.toml"
    port_way = "bedrock_edition_address"

    def download(
        self,
        target_directory: Path,
        console: Console | None = None,
        skip_if_hash: str | None = None,
    ) -> DownloadedCore | None:
        import httpx

        from luminesk.utils.github_releases import get_release_asset_info

        arch = platform.machine().lower()

        if "arm" in arch or "aarch" in arch:
            asset_name = "pumpkin-ARM64-Linux"
        else:
            asset_name = "pumpkin-X64-Linux"

        computed_hash = "nightly"
        download_link = f"https://github.com/Pumpkin-MC/Pumpkin/releases/download/nightly/{asset_name}"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                download_link, computed_hash = get_release_asset_info(
                    client, self.url, asset_name, tag="nightly"
                )
        except Exception:
            pass

        target_path = target_directory / "pumpkin"

        if (
            skip_if_hash is not None
            and skip_if_hash == computed_hash
            and target_path.is_file()
        ):
            return None

        download_url(download_link, target_path, console=console)

        # Make the binary executable
        try:
            os.chmod(target_path, 0o755)
        except OSError:
            pass

        return DownloadedCore(executable_path=target_path, hash=computed_hash)
