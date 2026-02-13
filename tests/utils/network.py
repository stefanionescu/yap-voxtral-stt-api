"""Network and WebSocket utilities for client scripts."""

from __future__ import annotations

import socket as _sock
from contextlib import suppress
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from params import config


def ws_url(server: str, secure: bool) -> str:
    """Generate a WebSocket URL for the server endpoint."""
    server = (server or "").strip()
    if server.startswith(("ws://", "wss://")):
        parsed = urlparse(server)
        scheme = parsed.scheme
        base_path = (parsed.path or "").rstrip("/")
        if not base_path.endswith(config.WS_ENDPOINT_PATH):
            base_path = config.WS_ENDPOINT_PATH if not base_path else f"{base_path}{config.WS_ENDPOINT_PATH}"
        return urlunparse(
            (
                scheme,
                parsed.netloc,
                base_path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ),
        )
    if server.startswith(("http://", "https://")):
        parsed = urlparse(server)
        use_secure = (parsed.scheme == "https") or secure
        scheme = "wss" if use_secure else "ws"
        base_path = parsed.path.rstrip("/")
        if not base_path.endswith(config.WS_ENDPOINT_PATH):
            base_path = f"{base_path}{config.WS_ENDPOINT_PATH}"
        return urlunparse((scheme, parsed.netloc, base_path, "", parsed.query, parsed.fragment))
    scheme = "wss" if secure else "ws"
    host = server.rstrip("/")
    return f"{scheme}://{host}{config.WS_ENDPOINT_PATH}"


def append_auth_query(url: str, api_key: str, override: bool = False) -> str:
    """Append the auth query parameter expected by the server.

    - When override=False (warmup behavior), only sets if missing.
    - When override=True (bench behavior), always sets/replaces.
    """
    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if override or ("api_key" not in query_params):
        query_params["api_key"] = api_key
    new_query = urlencode(query_params)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def is_cloud_host(server: str) -> bool:
    s = (server or "").strip().lower()
    if any(m in s for m in config.CLOUD_HOST_MARKERS):
        return True
    if any(x in s for x in config.LOCALHOST_IDENTIFIERS):
        return False
    try:
        parsed = urlparse(s if s.startswith(("http://", "https://", "ws://", "wss://")) else ("https://" + s))
        host = parsed.netloc.split("@")[-1].split(":")[0]
    except Exception:
        host = s
    if any(host.startswith(pb) for pb in config.PRIVATE_IP_BLOCKS):
        return False
    return "." in host


def enable_tcp_nodelay(ws) -> None:
    """Best-effort enable TCP_NODELAY on a websockets connection transport."""
    transport = getattr(ws, "transport", None)
    if transport is not None:
        sock = transport.get_extra_info("socket")
        if sock is not None:
            with suppress(Exception):
                sock.setsockopt(_sock.IPPROTO_TCP, _sock.TCP_NODELAY, 1)


__all__ = [
    "append_auth_query",
    "enable_tcp_nodelay",
    "is_cloud_host",
    "ws_url",
]
