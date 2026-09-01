from __future__ import annotations

import gzip
from pathlib import Path

import httpx
import pytest

from luminesk_cli.domain.errors import SecurityError
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.fetch import SecureFetcher


def test_fetch_streams_into_content_cache(tmp_path: Path) -> None:
    content = b"artifact bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/artifact"
        return httpx.Response(200, content=content)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = SecureFetcher(ContentCache(tmp_path / "cache"), client=client)

    blob = fetcher.fetch(
        "https://fixtures.invalid/artifact",
        max_size=1024,
        allow_private_network=True,
    )

    assert blob.path.read_bytes() == content
    assert blob.digest.startswith("sha256:")


def test_fetch_compares_expected_size_after_content_decoding(tmp_path: Path) -> None:
    content = b"general:\n  motd: fixture server\n"
    encoded = gzip.compress(content)

    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=encoded,
                headers={
                    "content-encoding": "gzip",
                    "content-length": str(len(encoded)),
                },
            )
        )
    )
    fetcher = SecureFetcher(ContentCache(tmp_path / "cache"), client=client)

    blob = fetcher.fetch(
        "https://fixtures.invalid/artifact",
        max_size=len(content),
        expected_size=len(content),
        allow_private_network=True,
    )

    assert len(encoded) != len(content)
    assert blob.size == len(content)
    assert blob.path.read_bytes() == content


def test_fetch_rejects_oversize_body(tmp_path: Path) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"x" * 11)
        )
    )
    fetcher = SecureFetcher(ContentCache(tmp_path / "cache"), client=client)

    with pytest.raises(SecurityError, match="size limit"):
        fetcher.fetch(
            "https://fixtures.invalid/artifact",
            max_size=10,
            allow_private_network=True,
        )


def test_fetch_revalidates_redirect_target(tmp_path: Path) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                302, headers={"location": "http://127.0.0.1/secret"}
            )
        )
    )
    fetcher = SecureFetcher(
        ContentCache(tmp_path / "cache"),
        client=client,
        address_resolver=lambda host, port: ["93.184.216.34"],
    )

    with pytest.raises(SecurityError):
        fetcher.fetch("https://example.com/artifact", max_size=10)


def test_fetch_drops_all_credentials_on_cross_host_redirect(tmp_path: Path) -> None:
    seen: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        if request.url.host == "origin.example":
            return httpx.Response(
                302,
                headers={"location": "https://cdn.example/artifact"},
            )
        return httpx.Response(200, content=b"artifact")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = SecureFetcher(ContentCache(tmp_path / "cache"), client=client)

    fetcher.fetch(
        "https://origin.example/artifact",
        max_size=100,
        allow_private_network=True,
        headers={
            "Authorization": "Bearer secret",
            "PRIVATE-TOKEN": "gitlab-secret",
            "Cookie": "session=secret",
        },
    )

    assert "authorization" in seen[0]
    assert "private-token" in seen[0]
    assert "cookie" in seen[0]
    assert "authorization" not in seen[1]
    assert "private-token" not in seen[1]
    assert "cookie" not in seen[1]


def test_fetch_rejects_digest_mismatch(tmp_path: Path) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"unexpected")
        )
    )
    fetcher = SecureFetcher(ContentCache(tmp_path / "cache"), client=client)

    with pytest.raises(SecurityError, match="digest"):
        fetcher.fetch(
            "https://fixtures.invalid/artifact",
            max_size=100,
            expected_digest=f"sha256:{'0' * 64}",
            allow_private_network=True,
        )
