from __future__ import annotations

import subprocess
from pathlib import Path

from rich.console import Console

from luminesk.core.base import PythonCore
from luminesk.models.manager import DownloadedCore
from luminesk.utils.docker import get_docker_binary


class EndstoneCore(PythonCore):
    id = "endstone"
    name = "Endstone"
    required_setup = True
    description = {
        "en": "Endstone brings the Minecraft Bedrock Dedicated Server (BDS) into the Python/C++ ecosystem.",
        "ru": "Endstone интегрирует Minecraft Bedrock Dedicated Server (BDS) в экосистему Python/C++.",
        "uk": "Endstone інтегрує Minecraft Bedrock Dedicated Server (BDS) в екосистему Python/C++.",
        "ja": "Endstone は、Minecraft Bedrock Dedicated Server（BDS）を Python/C++ エコシステムへ統合します。",
        "zh": "Endstone 将 Minecraft Bedrock Dedicated Server（BDS）集成到 Python/C++ 生态系统中。",
    }
    url = "https://github.com/EndstoneMC/Endstone"
    config_file = "server.properties"
    port_way = "server-port"

    def download(
        self,
        target_directory: Path,
        console: Console | None = None,
        skip_if_hash: str | None = None,
    ) -> DownloadedCore | None:
        import hashlib

        import httpx

        computed_hash = "latest"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get("https://pypi.org/pypi/endstone/json")
                resp.raise_for_status()
                data = resp.json()
                urls = data.get("urls", [])
                if urls:
                    urls_sorted = sorted(urls, key=lambda u: u.get("filename", ""))
                    sha256_list = []

                    for u in urls_sorted:
                        digests = u.get("digests", {})

                        if isinstance(digests, dict) and "sha256" in digests:
                            sha256_list.append(digests["sha256"])

                    if sha256_list:
                        combined = "".join(sha256_list)
                        computed_hash = hashlib.sha256(combined.encode()).hexdigest()
        except Exception:
            pass

        executable_path = target_directory / ".venv" / "bin" / "endstone"

        if (
            skip_if_hash is not None
            and skip_if_hash == computed_hash
            and executable_path.is_file()
        ):
            return None

        # We will create a local python venv and install endstone inside it using a Python 3.13 container
        docker_bin = get_docker_binary()

        from luminesk.core.launcher import ensure_docker_image

        ensure_docker_image("python:3.13-slim", docker_bin=docker_bin, console=console)

        from luminesk.core.messages import t

        status_msg = t("core.endstone.installing")

        def run_install():
            return subprocess.run(
                [
                    docker_bin,
                    "run",
                    "--rm",
                    "-v",
                    f"{str(target_directory.resolve()).replace('\\', '/')}:/app",
                    "-w",
                    "/app",
                    "python:3.13-slim",
                    "sh",
                    "-c",
                    "python -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install endstone",
                ],
                capture_output=True,
                text=True,
            )

        if console is not None:
            with console.status(status_msg, spinner="dots"):
                res = run_install()
        else:
            res = run_install()

        if res.returncode != 0:
            raise RuntimeError(
                t("core.endstone.install_failed", error=res.stderr or res.stdout)
            )

        return DownloadedCore(
            executable_path=executable_path,
            hash=computed_hash,
        )

    def get_docker_image(self) -> str:
        return "python:3.13-slim"

    def get_run_command(self, executable_name: str) -> str:
        return '.venv/bin/python -c "from endstone.cli import main; import sys; sys.exit(main())"'
