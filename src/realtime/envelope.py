"""WebSocket adapter for wrapping vLLM realtime protocol messages."""

from __future__ import annotations

from typing import Any
from collections.abc import Callable
from dataclasses import dataclass

import orjson
from fastapi import WebSocket, WebSocketDisconnect

from src.state import EnvelopeState
from src.config.websocket import (
    WS_ERROR_INTERNAL,
    WS_KEY_TYPE,
    WS_KEY_PAYLOAD,
    WS_KEY_REQUEST_ID,
    WS_KEY_SESSION_ID,
)


@dataclass(slots=True)
class _TranscriptState:
    request_id: str = "unknown"
    committed_text: str = ""
    visible_text: str = ""
    segment_text: str = ""
    dedup_prefix_len: int = 0


class EnvelopeWebSocket:
    """A minimal adapter that lets vLLM send raw Realtime events while clients see JSON envelopes."""

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
        self._suppress_done_count: int = 0
        self._tx = _TranscriptState()

    def suppress_next_done(self) -> None:
        """Suppress the next client-visible completion frames (final/done).

        Used for internal rolling: vLLM still ends a segment with transcription.done,
        but clients should see a continuous token stream.
        """
        self._suppress_done_count += 1

    async def send_status(self, payload: dict[str, Any]) -> None:
        if self._state.touch is not None:
            self._state.touch()
        rid = self._state.inflight_request_id or self._state.active_request_id or self._state.request_id
        envelope = {
            WS_KEY_TYPE: "status",
            WS_KEY_SESSION_ID: self._state.session_id,
            WS_KEY_REQUEST_ID: rid,
            WS_KEY_PAYLOAD: payload or {},
        }
        await self._safe_send_envelope(envelope)

    async def _safe_send_envelope(self, envelope: dict[str, Any]) -> None:
        try:
            await self._ws.send_text(orjson.dumps(envelope).decode("utf-8"))
        except WebSocketDisconnect:
            if self._on_disconnect is not None:
                self._on_disconnect()
            raise
        except Exception:
            if self._on_disconnect is not None:
                self._on_disconnect()
            raise

    def _reset_transcript_if_needed(self) -> None:
        rid = self._state.inflight_request_id or self._state.active_request_id or self._state.request_id
        if self._tx.request_id == rid:
            return
        self._tx = _TranscriptState(request_id=rid)

    @staticmethod
    def _find_overlap(a_suffix: str, b_prefix: str) -> int:
        """Return length of the longest suffix of a_suffix that is a prefix of b_prefix."""
        if not a_suffix or not b_prefix:
            return 0
        max_len = min(len(a_suffix), len(b_prefix))
        # Brute force on a small window; good enough for short overlaps.
        for i in range(max_len, 0, -1):
            if a_suffix.endswith(b_prefix[:i]):
                return i
        return 0

    def _maybe_update_dedup_prefix(self) -> None:
        if not self._tx.committed_text or not self._tx.segment_text:
            return

        # Only look at bounded windows for performance.
        tail = self._tx.committed_text[-2000:]
        head = self._tx.segment_text[:2000]
        overlap = self._find_overlap(tail, head)
        if overlap <= 0:
            return

        candidate_cut = int(overlap)
        if candidate_cut <= int(self._tx.dedup_prefix_len):
            return
        candidate_merged = self._tx.committed_text + self._tx.segment_text[candidate_cut:]
        if candidate_merged.startswith(self._tx.visible_text):
            self._tx.dedup_prefix_len = candidate_cut

    async def send_text(self, text: str) -> None:
        if self._state.touch is not None:
            self._state.touch()
        try:
            event = orjson.loads(text)
        except Exception:
            envelope = {
                WS_KEY_TYPE: "realtime.raw",
                WS_KEY_SESSION_ID: self._state.session_id,
                WS_KEY_REQUEST_ID: self._state.request_id,
                WS_KEY_PAYLOAD: {"raw": text},
            }
            await self._safe_send_envelope(envelope)
            return

        msg_type = event.get("type")
        if not isinstance(msg_type, str):
            msg_type = "realtime.unknown"

        self._reset_transcript_if_needed()

        if msg_type == "transcription.delta":
            delta = event.get("delta") if isinstance(event, dict) else None
            if isinstance(delta, str) and delta:
                self._tx.segment_text += delta
                self._maybe_update_dedup_prefix()

                merged = self._tx.committed_text + self._tx.segment_text[self._tx.dedup_prefix_len :]
                if merged.startswith(self._tx.visible_text):
                    out = merged[len(self._tx.visible_text) :]
                    if out:
                        envelope = {
                            WS_KEY_TYPE: "token",
                            WS_KEY_SESSION_ID: self._state.session_id,
                            WS_KEY_REQUEST_ID: self._tx.request_id,
                            WS_KEY_PAYLOAD: {"text": out},
                        }
                        await self._safe_send_envelope(envelope)
                        self._tx.visible_text = merged
            return

        if msg_type == "transcription.done":
            if self._state.inflight_request_id == self._state.request_id:
                self._state.inflight_request_id = None

            txt = event.get("text") if isinstance(event, dict) else None
            if isinstance(txt, str):
                self._tx.segment_text = txt
            self._maybe_update_dedup_prefix()

            merged = self._tx.committed_text + self._tx.segment_text[self._tx.dedup_prefix_len :]
            if merged.startswith(self._tx.visible_text):
                out = merged[len(self._tx.visible_text) :]
                if out:
                    token_env = {
                        WS_KEY_TYPE: "token",
                        WS_KEY_SESSION_ID: self._state.session_id,
                        WS_KEY_REQUEST_ID: self._tx.request_id,
                        WS_KEY_PAYLOAD: {"text": out},
                    }
                    await self._safe_send_envelope(token_env)

            # Segment complete.
            self._tx.committed_text = merged
            self._tx.visible_text = merged
            self._tx.segment_text = ""
            self._tx.dedup_prefix_len = 0

            if self._suppress_done_count > 0:
                self._suppress_done_count -= 1
                return

            final_env = {
                WS_KEY_TYPE: "final",
                WS_KEY_SESSION_ID: self._state.session_id,
                WS_KEY_REQUEST_ID: self._tx.request_id,
                WS_KEY_PAYLOAD: {"normalized_text": merged},
            }
            done_env = {
                WS_KEY_TYPE: "done",
                WS_KEY_SESSION_ID: self._state.session_id,
                WS_KEY_REQUEST_ID: self._tx.request_id,
                WS_KEY_PAYLOAD: {"usage": (event.get("usage") if isinstance(event, dict) else {}) or {}},
            }
            await self._safe_send_envelope(final_env)
            await self._safe_send_envelope(done_env)
            # Utterance complete; reset transcript assembly for safety.
            self._tx = _TranscriptState(request_id=self._tx.request_id)
            return

        if msg_type == "error":
            if self._state.inflight_request_id == self._state.request_id:
                self._state.inflight_request_id = None
            # Any pending internal-roll suppression is no longer meaningful if vLLM errored.
            self._suppress_done_count = 0

            message = ""
            code = WS_ERROR_INTERNAL
            if isinstance(event, dict):
                ev_msg = event.get("error")
                ev_code = event.get("code")
                if isinstance(ev_msg, str):
                    message = ev_msg
                if isinstance(ev_code, str) and ev_code.strip():
                    code = ev_code.strip()

            envelope = {
                WS_KEY_TYPE: "error",
                WS_KEY_SESSION_ID: self._state.session_id,
                WS_KEY_REQUEST_ID: self._tx.request_id,
                WS_KEY_PAYLOAD: {"code": code, "message": message or "error", "details": {"reason_code": code}},
            }
            await self._safe_send_envelope(envelope)
            self._tx = _TranscriptState(request_id=self._tx.request_id)
            return

        # Fall back to forwarding other realtime event types as-is (still wrapped).
        payload: dict[str, Any] = {k: v for k, v in event.items() if k != "type"} if isinstance(event, dict) else {}
        envelope = {
            WS_KEY_TYPE: msg_type,
            WS_KEY_SESSION_ID: self._state.session_id,
            WS_KEY_REQUEST_ID: self._tx.request_id,
            WS_KEY_PAYLOAD: payload,
        }
        await self._safe_send_envelope(envelope)

    async def close(self, *, code: int = 1000, reason: str | None = None) -> None:
        await self._ws.close(code=code, reason=reason or "")


__all__ = ["EnvelopeWebSocket"]
