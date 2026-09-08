from __future__ import annotations

import pytest

from luminesk_cli.domain.errors import SecurityError
from luminesk_cli.infrastructure.cache import ContentCache
from luminesk_cli.infrastructure.fetch import SecureFetcher
from luminesk_cli.infrastructure.security.network import validate_remote_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:secret@example.com/file",
        "https://127.0.0.1/file",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/file",
    ],
)
def test_remote_url_policy_blocks_unsafe_destinations(url: str) -> None:
    with pytest.raises(SecurityError):
        validate_remote_url(url)


def test_remote_url_policy_checks_dns_results() -> None:
    with pytest.raises(SecurityError, match="private"):
        validate_remote_url(
            "https://attacker.example/file",
            resolver=lambda host, port: ["10.0.0.1"],
        )


def test_remote_url_policy_accepts_public_https() -> None:
    assert (
        validate_remote_url(
            "https://example.com/file",
            resolver=lambda host, port: ["93.184.216.34"],
        )
        == "https://example.com/file"
    )


def test_fetch_blocks_dns_rebinding_at_connection_time(tmp_path) -> None:
    answers = iter(
        [
            ["93.184.216.34"],
            ["127.0.0.1"],
        ]
    )
    calls: list[tuple[str, int]] = []

    def rebinding_resolver(host: str, port: int) -> list[str]:
        calls.append((host, port))
        return next(answers)

    fetcher = SecureFetcher(
        ContentCache(tmp_path / "cache"),
        address_resolver=rebinding_resolver,
    )

    with pytest.raises(SecurityError, match="private or special"):
        fetcher.fetch("https://attacker.example/artifact", max_size=1024)

    assert calls == [
        ("attacker.example", 443),
        ("attacker.example", 443),
    ]


def test_remote_url_policy_rejects_invalid_dns_result() -> None:
    with pytest.raises(SecurityError, match="invalid IP"):
        validate_remote_url(
            "https://attacker.example/file",
            resolver=lambda host, port: ["not-an-ip"],
        )
