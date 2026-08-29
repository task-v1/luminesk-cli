from __future__ import annotations

import pytest

from luminesk_cli.domain.errors import SecurityError
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
