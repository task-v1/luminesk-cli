from __future__ import annotations

from pathlib import Path

from rich.console import Console

from luminesk.core.base import GoCore
from luminesk.models.manager import DownloadedCore


class DragonflyCore(GoCore):
    id = "dragonfly"
    name = "Dragonfly"
    description = {
        "en": "A highly asynchronous server software for Minecraft: Bedrock Edition written in Go.",
        "ru": "Высокоасинхронное серверное ПО для Minecraft: Bedrock Edition, написанное на Go.",
        "uk": "Високоасинхронне серверне ПЗ для Minecraft: Bedrock Edition, написане на Go.",
        "ja": "Go で開発された、高度な非同期処理を備える Minecraft: Bedrock Edition 向けサーバーソフトウェア。",
        "zh": "使用 Go 编写的高度异步 Minecraft: Bedrock Edition 服务器软件。",
    }
    url = "https://github.com/df-mc/dragonfly"
    config_file = "config.toml"
    port_way = "Network.Address"
    dont_create_config = True

    def download(
        self,
        target_directory: Path,
        console: Console | None = None,
        skip_if_hash: str | None = None,
    ) -> DownloadedCore | None:
        import httpx

        from luminesk.utils.github_releases import fetch_json, parse_github_repo_url

        latest_tag = "master"
        latest_sha = "latest"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                owner, repo = parse_github_repo_url(self.url)
                api_url = f"https://api.github.com/repos/{owner}/{repo}/tags"
                tags = fetch_json(client, api_url)
                if isinstance(tags, list) and tags:
                    latest_tag = tags[0]["name"]  # type: ignore
                    latest_sha = tags[0]["commit"]["sha"]  # type: ignore
        except Exception:
            pass

        executable_path = target_directory / "dragonfly"

        if (
            skip_if_hash is not None
            and skip_if_hash == latest_sha
            and executable_path.is_file()
        ):
            return None

        main_go_path = target_directory / "main.go"
        go_mod_path = target_directory / "go.mod"

        main_go_content = """package main

import (
	"fmt"
	"github.com/df-mc/dragonfly/server"
	"github.com/df-mc/dragonfly/server/player/chat"
	"github.com/pelletier/go-toml"
	"log/slog"
	"os"
)

func main() {
	slog.SetLogLoggerLevel(slog.LevelDebug)
	chat.Global.Subscribe(chat.StdoutSubscriber{})
	conf, err := readConfig(slog.Default())
	if err != nil {
		panic(err)
	}

	srv := conf.New()
	srv.CloseOnProgramEnd()

	srv.Listen()
	for p := range srv.Accept() {
		_ = p
	}
}

func readConfig(log *slog.Logger) (server.Config, error) {
	c := server.DefaultConfig()
	var zero server.Config
	if _, err := os.Stat("config.toml"); os.IsNotExist(err) {
		data, err := toml.Marshal(c)
		if err != nil {
			return zero, fmt.Errorf("encode default config: %v", err)
		}
		if err := os.WriteFile("config.toml", data, 0644); err != nil {
			return zero, fmt.Errorf("create default config: %v", err)
		}
		return c.Config(log)
	}
	data, err := os.ReadFile("config.toml")
	if err != nil {
		return zero, fmt.Errorf("read config: %v", err)
	}
	if err := toml.Unmarshal(data, &c); err != nil {
		return zero, fmt.Errorf("decode config: %v", err)
	}
	return c.Config(log)
}
"""
        go_mod_content = """module server

go 1.26
"""

        if not main_go_path.exists():
            main_go_path.write_text(main_go_content, encoding="utf-8")

        if not go_mod_path.exists():
            go_mod_path.write_text(go_mod_content, encoding="utf-8")

        import subprocess

        from luminesk.utils.docker import get_docker_binary

        docker_bin = get_docker_binary()

        from luminesk.core.launcher import ensure_docker_image

        ensure_docker_image(
            "golang:1.26-alpine", docker_bin=docker_bin, console=console
        )

        from luminesk.core.messages import t

        status_msg = t("core.dragonfly.compiling")

        go_get_cmd = ""

        if latest_tag != "master":
            go_get_cmd = f"go get github.com/df-mc/dragonfly/server@{latest_tag} && "

        compile_cmd = f"{go_get_cmd}go mod tidy && go build -o dragonfly main.go"

        def run_compile():
            return subprocess.run(
                [
                    docker_bin,
                    "run",
                    "--rm",
                    "-v",
                    f"{str(target_directory.resolve()).replace('\\', '/')}:/app",
                    "-w",
                    "/app",
                    "golang:1.26-alpine",
                    "sh",
                    "-c",
                    compile_cmd,
                ],
                capture_output=True,
                text=True,
            )

        if console is not None:
            with console.status(status_msg, spinner="dots"):
                res = run_compile()
        else:
            res = run_compile()

        if res.returncode != 0:
            raise RuntimeError(
                t("core.dragonfly.compile_failed", error=res.stderr or res.stdout)
            )

        return DownloadedCore(executable_path=executable_path, hash=latest_sha)
