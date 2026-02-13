"""WebSocket authentication helpers."""

from __future__ import annotations

from fastapi import WebSocket

from src.config.secrets import get_voxtral_api_key


def get_api_key(ws: WebSocket) -> str:
    # Query param is easiest for WS clients.
    key = (ws.query_params.get("api_key") or "").strip()
    if key:
        return key
    return (ws.headers.get("x-api-key") or "").strip()


def validate_api_key(api_key: str) -> bool:
    expected = get_voxtral_api_key()
    if not expected:
        # Misconfiguration: server has no key set. Treat as locked down.
        return False
    return api_key == expected


async def authenticate_websocket(ws: WebSocket) -> bool:
    return validate_api_key(get_api_key(ws))


__all__ = ["authenticate_websocket", "get_api_key", "validate_api_key"]
