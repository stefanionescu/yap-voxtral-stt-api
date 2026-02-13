"""Error helpers for the WebSocket JSON envelope."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.config.websocket import WS_KEY_TYPE, WS_KEY_PAYLOAD, WS_KEY_REQUEST_ID, WS_KEY_SESSION_ID

logger = logging.getLogger(__name__)


def build_error_payload(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    reason_code: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if details:
        payload["details"] = details
    if reason_code:
        payload["reason_code"] = reason_code
    return payload


def build_envelope(
    msg_type: str,
    session_id: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        WS_KEY_TYPE: msg_type,
        WS_KEY_SESSION_ID: session_id,
        WS_KEY_REQUEST_ID: request_id,
        WS_KEY_PAYLOAD: payload or {},
    }


async def safe_send_text(ws: WebSocket, text: str) -> bool:
    try:
        await ws.send_text(text)
    except WebSocketDisconnect:
        return False
    except Exception:
        logger.debug("WebSocket send failed", exc_info=True)
        return False
    return True


async def safe_send_envelope(
    ws: WebSocket,
    *,
    msg_type: str,
    session_id: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
) -> bool:
    return await safe_send_text(ws, json.dumps(build_envelope(msg_type, session_id, request_id, payload)))


async def send_error(
    ws: WebSocket,
    *,
    session_id: str | None,
    request_id: str | None,
    error_code: str,
    message: str,
    reason_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> bool:
    return await safe_send_envelope(
        ws,
        msg_type="error",
        session_id=session_id or "unknown",
        request_id=request_id or "unknown",
        payload=build_error_payload(error_code, message, details=details, reason_code=reason_code),
    )


async def reject_connection(
    ws: WebSocket,
    *,
    error_code: str,
    message: str,
    close_code: int,
) -> None:
    # Accept so we can send a structured error, then close.
    try:
        await ws.accept()
    except Exception:
        # If accept fails, nothing else to do.
        return
    await send_error(
        ws,
        session_id="unknown",
        request_id="unknown",
        error_code=error_code,
        message=message,
        reason_code=error_code,
    )
    try:
        await ws.close(code=close_code, reason=message)
    except Exception:
        return


__all__ = [
    "build_error_payload",
    "build_envelope",
    "safe_send_envelope",
    "send_error",
    "reject_connection",
]
