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


def resolve_remote_addresses(
    host: str,
    port: int,
    *,
    allow_private_network: bool = False,
    resolver: AddressResolver = _resolve_addresses,
    url: str | None = None,
) -> tuple[str, ...]:
    """Resolve once and return normalized addresses allowed by the policy."""

    try:
        literal = ipaddress.ip_address(host.strip("[]"))
        raw_addresses = [str(literal)]
    except ValueError:
        try:
            raw_addresses = list(resolver(host, port))
        except OSError as exc:
            raise SecurityError(
                f"cannot resolve remote host {host}: {exc}", url=url
            ) from exc

    if not raw_addresses:
        raise SecurityError(f"remote host {host} resolved to no addresses", url=url)

    addresses: list[str] = []

    for raw_address in raw_addresses:
        try:
            address = str(ipaddress.ip_address(raw_address))
        except ValueError as exc:
            raise SecurityError(
                f"remote host {host} resolved to an invalid IP address",
                url=url,
                address=raw_address,
            ) from exc

        if address not in addresses:
            addresses.append(address)

    if not allow_private_network:
        blocked = sorted(
            address for address in addresses if not _is_public_address(address)
        )

        if blocked:
            raise SecurityError(
                f"remote host resolves to a private or special address: {blocked[0]}",
                url=url,
                address=blocked[0],
            )

    return tuple(addresses)


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

    resolve_remote_addresses(
        host,
        port,
        allow_private_network=False,
        resolver=resolver,
        url=url,
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
