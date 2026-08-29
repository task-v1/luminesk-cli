"""SSRF-resistant validation applied before every outbound request."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import urljoin, urlsplit

from luminesk_cli.domain.errors import SecurityError

AddressResolver = Callable[[str, int], Iterable[str]]


def _resolve_addresses(host: str, port: int) -> Iterable[str]:
    return {
        str(item[4][0])
        for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    }


def _is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return bool(ip.is_global)


def validate_remote_url(
    url: str,
    *,
    allow_http: bool = False,
    allow_private_network: bool = False,
    resolver: AddressResolver = _resolve_addresses,
) -> str:
    """Validate scheme, credentials, port and all resolved IP addresses."""

    parsed = urlsplit(url)
    allowed_schemes = {"https"}

    if allow_http:
        allowed_schemes.add("http")

    if parsed.scheme not in allowed_schemes:
        raise SecurityError(
            "remote URL must use HTTPS unless allow_http is enabled", url=url
        )

    if parsed.username is not None or parsed.password is not None:
        raise SecurityError("credentials are forbidden in remote URLs", url=url)

    host = parsed.hostname

    if not host:
        raise SecurityError("remote URL has no hostname", url=url)

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise SecurityError("remote URL has an invalid port", url=url) from exc

    if allow_private_network:
        return url

    try:
        address = ipaddress.ip_address(host.strip("[]"))
        addresses = [str(address)]
    except ValueError:
        try:
            addresses = list(resolver(host, port))
        except OSError as exc:
            raise SecurityError(
                f"cannot resolve remote host {host}: {exc}", url=url
            ) from exc

    if not addresses:
        raise SecurityError(f"remote host {host} resolved to no addresses", url=url)

    blocked = sorted(address for address in addresses if not _is_public_address(address))

    if blocked:
        raise SecurityError(
            f"remote host resolves to a private or special address: {blocked[0]}",
            url=url,
            address=blocked[0],
        )

    return url


def validate_redirect(
    current_url: str,
    location: str,
    *,
    allow_http: bool = False,
    allow_private_network: bool = False,
    resolver: AddressResolver = _resolve_addresses,
) -> str:
    destination = urljoin(current_url, location)
    return validate_remote_url(
        destination,
        allow_http=allow_http,
        allow_private_network=allow_private_network,
        resolver=resolver,
    )
