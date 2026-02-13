"""Adapter between Yap-style envelopes and vLLM's RealtimeConnection."""

from __future__ import annotations

import logging
import contextlib
from typing import Any

from fastapi import WebSocket

from .state import EnvelopeState
from .envelope_ws import EnvelopeWebSocket

logger = logging.getLogger(__name__)


class RealtimeConnectionAdapter:
    def __init__(
        self,
        *,
        ws: WebSocket,
        state: EnvelopeState,
        serving_realtime: Any,
        allowed_model_name: str,
    ) -> None:
        self._state = state
        self._allowed_model_name = allowed_model_name

        from vllm.entrypoints.openai.realtime.connection import (  # noqa: PLC0415
            RealtimeConnection,
        )

        self._conn: RealtimeConnection | None = None

        def _mark_disconnected() -> None:
            if self._conn is not None:
                try:
                    self._conn._is_connected = False
                except Exception:
                    return

        # vLLM expects a starlette-style WebSocket for sending; we wrap sends into envelopes.
        send_ws = EnvelopeWebSocket(ws, state, on_disconnect=_mark_disconnected)

        self._conn = RealtimeConnection(send_ws, serving_realtime)
        # We run our own receive loop, so we mark the vLLM connection as active
        # (RealtimeConnection normally flips this in handle_connection()).
        self._conn._is_connected = True

        self._initialized = False

    async def ensure_initialized(self) -> None:
        if self._initialized:
            return
        await self.handle_event("session.update", {"model": self._allowed_model_name})
        self._initialized = True

    async def handle_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "session.update":
            self._initialized = True
        event: dict[str, Any] = {"type": event_type}
        event.update(payload)
        if self._conn is None:
            raise RuntimeError("realtime connection is not initialized")
        await self._conn.handle_event(event)

    async def cancel(self) -> None:
        """Best-effort cancel current generation + clear buffers."""
        try:
            if self._conn is None:
                return

            # Drain queued audio to stop quickly.
            q = getattr(self._conn, "audio_queue", None)
            if q is not None:
                with contextlib.suppress(Exception):
                    while not q.empty():
                        q.get_nowait()

            # vLLM exposes an async cleanup() that cancels generation task.
            await self._conn.cleanup()
        except Exception:
            logger.debug("vllm realtime cleanup failed", exc_info=True)


__all__ = ["RealtimeConnectionAdapter"]
