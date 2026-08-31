"""HTTP transport that enforces the network policy at connection time."""

from __future__ import annotations

from collections.abc import Iterable

import httpcore
import httpx

from luminesk_cli.domain.errors import SecurityError
from luminesk_cli.infrastructure.security.network import (
    AddressResolver,
    _resolve_addresses,
    resolve_remote_addresses,
)

ALLOW_PRIVATE_NETWORK_EXTENSION = "luminesk_allow_private_network"


class _PolicyNetworkBackend(httpcore.NetworkBackend):
    def __init__(
        self,
        *,
        allow_private_network: bool,
        resolver: AddressResolver,
        backend: httpcore.NetworkBackend | None = None,
    ) -> None:
        self._allow_private_network = allow_private_network
        self._resolver = resolver
        self._backend = backend or httpcore.SyncBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:
        addresses = resolve_remote_addresses(
            host,
            port,
            allow_private_network=self._allow_private_network,
            resolver=self._resolver,
        )
        last_error: httpcore.ConnectError | httpcore.ConnectTimeout | None = None

        for address in addresses:
            try:
                return self._backend.connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc

        assert last_error is not None
        raise last_error

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:
        del path, timeout, socket_options
        raise SecurityError("UNIX sockets are forbidden for remote HTTP requests")

    def sleep(self, seconds: float) -> None:
        self._backend.sleep(seconds)


class _PolicyHTTPTransport(httpx.HTTPTransport):
    def __init__(
        self,
        *,
        allow_private_network: bool,
        resolver: AddressResolver,
    ) -> None:
        self._pool = httpcore.ConnectionPool(
            ssl_context=httpx.create_ssl_context(trust_env=False),
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=5.0,
            network_backend=_PolicyNetworkBackend(
                allow_private_network=allow_private_network,
                resolver=resolver,
            ),
        )


class SecureHTTPTransport(httpx.BaseTransport):
    """Select a public-only or explicitly private-capable connection pool."""

    def __init__(
        self,
        *,
        resolver: AddressResolver = _resolve_addresses,
    ) -> None:
        self._public = _PolicyHTTPTransport(
            allow_private_network=False,
            resolver=resolver,
        )
        self._private = _PolicyHTTPTransport(
            allow_private_network=True,
            resolver=resolver,
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        transport = (
            self._private
            if request.extensions.get(ALLOW_PRIVATE_NETWORK_EXTENSION) is True
            else self._public
        )
        return transport.handle_request(request)

    def close(self) -> None:
        self._public.close()
        self._private.close()


def create_secure_client(
    *,
    resolver: AddressResolver = _resolve_addresses,
) -> httpx.Client:
    """Create the default bounded client without environment proxy routing."""

    return httpx.Client(
        transport=SecureHTTPTransport(resolver=resolver),
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=False,
        trust_env=False,
    )
