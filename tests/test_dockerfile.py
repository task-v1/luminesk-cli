from __future__ import annotations

from pathlib import Path

import pytest

from luminesk_cli.domain.errors import SecurityError, ValidationError
from luminesk_cli.infrastructure.dockerfile import (
    dockerfile_base_images,
    rewrite_dockerfile,
)


def test_dockerfile_images_ignore_named_stages_and_are_rewritten(
    tmp_path: Path,
) -> None:
    path = tmp_path / "Dockerfile"
    path.write_text(
        "FROM --platform=linux/amd64 golang:1.26 AS build\n"
        "RUN go build\n"
        "FROM build AS copied\n"
        "FROM alpine:3.23\n"
        "COPY --from=copied /out /out\n",
        encoding="utf-8",
    )

    assert dockerfile_base_images(path) == ("golang:1.26", "alpine:3.23")
    rewritten = rewrite_dockerfile(
        path.read_text(encoding="utf-8"),
        {
            "golang:1.26": f"golang@sha256:{'a' * 64}",
            "alpine:3.23": f"alpine@sha256:{'b' * 64}",
        },
    )

    assert "golang:1.26" not in rewritten
    assert "alpine:3.23" not in rewritten
    assert "FROM build AS copied" in rewritten


def test_dockerfile_dynamic_base_image_is_forbidden(tmp_path: Path) -> None:
    path = tmp_path / "Dockerfile"
    path.write_text("ARG BASE\nFROM ${BASE}\n", encoding="utf-8")

    with pytest.raises(SecurityError, match="dynamic"):
        dockerfile_base_images(path)


def test_dockerfile_rewrite_rejects_stale_build_lock() -> None:
    with pytest.raises(ValidationError, match="no longer present"):
        rewrite_dockerfile(
            "FROM alpine:3.23\n",
            {"debian:13": f"debian@sha256:{'a' * 64}"},
        )
