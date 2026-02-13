"""WebSocket adapter for wrapping vLLM realtime protocol messages."""

from __future__ import annotations

import json
from typing import Any
from collections.abc import Callable

from fastapi import WebSocket, WebSocketDisconnect

from src.config.websocket import WS_KEY_TYPE, WS_KEY_PAYLOAD, WS_KEY_REQUEST_ID, WS_KEY_SESSION_ID

from .state import EnvelopeState


class EnvelopeWebSocket:
    """A minimal adapter that lets vLLM send raw Realtime events while clients see Yap envelopes."""

    def __init__(
        self,
        ws: WebSocket,
        state: EnvelopeState,
        *,
        on_disconnect: Callable[[], None] | None = None,
    ) -> None:
        self._ws = ws
        self._state = state
        self._on_disconnect = on_disconnect

    async def send_text(self, text: str) -> None:
        try:
            event = json.loads(text)
        except Exception:
            envelope = {
                WS_KEY_TYPE: "realtime.raw",
                WS_KEY_SESSION_ID: self._state.session_id,
                WS_KEY_REQUEST_ID: self._state.request_id,
                WS_KEY_PAYLOAD: {"raw": text},
            }
            await self._ws.send_text(json.dumps(envelope))
            return

        msg_type = event.get("type")
        payload: dict[str, Any] = {}
        if isinstance(event, dict):
            payload = {k: v for k, v in event.items() if k != "type"}
        envelope = {
            WS_KEY_TYPE: msg_type if isinstance(msg_type, str) else "realtime.unknown",
            WS_KEY_SESSION_ID: self._state.session_id,
            WS_KEY_REQUEST_ID: self._state.request_id,
            WS_KEY_PAYLOAD: payload,
        }
        try:
            await self._ws.send_text(json.dumps(envelope))
        except WebSocketDisconnect:
            if self._on_disconnect is not None:
                self._on_disconnect()
            raise
        except Exception:
            if self._on_disconnect is not None:
                self._on_disconnect()
            raise

    async def close(self, *, code: int = 1000, reason: str | None = None) -> None:
        await self._ws.close(code=code, reason=reason or "")


__all__ = ["EnvelopeWebSocket"]
