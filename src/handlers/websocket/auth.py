"""WebSocket authentication helpers."""

from __future__ import annotations

from fastapi import WebSocket


def get_api_key(ws: WebSocket) -> str:
    # Query param is easiest for WS clients.
    key = (ws.query_params.get("api_key") or "").strip()
    if key:
        return key
    return (ws.headers.get("x-api-key") or "").strip()


def validate_api_key(api_key: str, expected: str) -> bool:
    if not expected:
        # Misconfiguration: server has no key set. Treat as locked down.
        return False
    return api_key == expected


async def authenticate_websocket(ws: WebSocket, *, expected_api_key: str) -> bool:
    return validate_api_key(get_api_key(ws), expected_api_key)


__all__ = ["authenticate_websocket", "get_api_key", "validate_api_key"]
