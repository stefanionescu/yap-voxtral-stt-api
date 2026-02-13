"""WebSocket message handling for streaming transcription clients."""

from __future__ import annotations

import json
import time
import asyncio
import logging

import config

logger = logging.getLogger(__name__)


class MessageHandler:
    """Process server messages and track timing/text for metrics."""

    def __init__(self, *, debug: bool = False) -> None:
        self.debug = debug

        # Text assembly
        self.final_text: str = ""

        # Timing
        self.partial_ts: list[float] = []
        self.last_partial_ts: float = config.DEFAULT_ZERO
        self.first_delta_ts: float | None = None
        self.final_recv_ts: float = config.DEFAULT_ZERO
        self.ready_recv_ts: float | None = None

        # Async coordination
        self.ready_event = asyncio.Event()
        self.done_event = asyncio.Event()

        # Error/rejection
        self.reject_reason: str | None = None
        self.error: str | None = None

    async def process_messages(self, ws, session_start: float) -> None:
        try:
            async for raw in ws:
                now = time.perf_counter()
                msg = self._parse(raw)
                if msg is None:
                    continue
                if self.debug:
                    logger.debug("recv: %s", msg)
                self._handle_message(msg, now, session_start)
        except Exception as exc:
            if self.error is None and not self.done_event.is_set():
                self.error = f"{type(exc).__name__}: {exc}"
            self.done_event.set()

    @staticmethod
    def _parse(raw) -> dict | None:
        try:
            if isinstance(raw, bytes | bytearray):
                raw = raw.decode("utf-8", errors="ignore")
            return json.loads(raw)
        except Exception:
            return None

    def _handle_message(self, msg: dict, now: float, session_start: float) -> None:
        msg_type = msg.get(config.PROTO_KEY_TYPE)
        payload = msg.get(config.PROTO_KEY_PAYLOAD) or {}

        if self.ready_recv_ts is None and msg_type in {
            config.PROTO_TYPE_SESSION_CREATED,
            config.PROTO_TYPE_SESSION_UPDATED,
        }:
            self.ready_recv_ts = now
            self.ready_event.set()
            return

        if msg_type == config.PROTO_TYPE_TRANSCRIPTION_DELTA:
            delta = payload.get("delta") if isinstance(payload, dict) else None
            if isinstance(delta, str) and delta:
                if self.first_delta_ts is None:
                    self.first_delta_ts = now
                self.final_text += delta
                self.partial_ts.append(now)
                self.last_partial_ts = now
            return

        if msg_type == config.PROTO_TYPE_TRANSCRIPTION_DONE:
            txt = payload.get("text") if isinstance(payload, dict) else None
            if isinstance(txt, str) and txt:
                self.final_text = txt
            self.final_recv_ts = now
            self.done_event.set()
            return

        if msg_type == config.PROTO_TYPE_ERROR:
            self.handle_error(payload if isinstance(payload, dict) else {"error": payload})
            self.done_event.set()
            return

    def handle_error(self, payload: dict) -> None:
        code = (payload.get("code") or "").strip()
        message = (payload.get("message") or payload.get("error") or "").strip()
        if code:
            self.error = f"{code}: {message}" if message else code
        else:
            self.error = message or "error"


__all__ = ["MessageHandler", "logger"]
