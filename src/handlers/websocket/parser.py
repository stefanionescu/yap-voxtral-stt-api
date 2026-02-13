"""Client message parsing/validation for the Yap-style envelope."""

from __future__ import annotations

import json
from typing import Any

from src.config.websocket import WS_KEY_TYPE, WS_KEY_PAYLOAD, WS_KEY_REQUEST_ID, WS_KEY_SESSION_ID


def parse_client_message(raw: str) -> dict[str, Any]:
    try:
        msg = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    if not isinstance(msg, dict):
        raise ValueError("message must be a JSON object")

    msg_type = msg.get(WS_KEY_TYPE)
    if not isinstance(msg_type, str) or not msg_type.strip():
        raise ValueError("message missing non-empty 'type'")

    session_id = msg.get(WS_KEY_SESSION_ID)
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("message missing non-empty 'session_id'")

    request_id = msg.get(WS_KEY_REQUEST_ID)
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("message missing non-empty 'request_id'")

    payload = msg.get(WS_KEY_PAYLOAD, {})
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("message 'payload' must be an object")

    # Normalize
    msg[WS_KEY_TYPE] = msg_type.strip()
    msg[WS_KEY_SESSION_ID] = session_id.strip()
    msg[WS_KEY_REQUEST_ID] = request_id.strip()
    msg[WS_KEY_PAYLOAD] = payload
    return msg


__all__ = ["parse_client_message"]
