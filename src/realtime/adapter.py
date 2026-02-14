"""Adapter between JSON envelopes and vLLM's RealtimeConnection."""

from __future__ import annotations

import asyncio
import logging
import contextlib
from typing import Any
from collections import deque

from fastapi import WebSocket
from vllm.entrypoints.openai.realtime.connection import RealtimeConnection

from src.state import EnvelopeState
from src.config.limits import ASR_SAMPLE_RATE_HZ
from src.config.vllm import VLLM_MAX_MODEL_LEN
from src.config.streaming import (
    STT_INTERNAL_ROLL,
    STT_MAX_BACKLOG_SECONDS,
    STT_SEGMENT_OVERLAP_SECONDS,
    STT_SEGMENT_SECONDS,
)

from .envelope import EnvelopeWebSocket

logger = logging.getLogger(__name__)

_ASR_BYTES_PER_SECOND: int = int(ASR_SAMPLE_RATE_HZ * 2)
_AUDIO_TOKEN_SECONDS: float = 0.08  # Voxtral realtime (~80ms/token)
_AUDIO_BYTES_PER_TOKEN: int = int(_ASR_BYTES_PER_SECOND * _AUDIO_TOKEN_SECONDS)  # ~2560 for 16kHz PCM16
_AUDIO_TOKEN_HEADROOM: int = 128  # leave room for text/system tokens


def _estimate_b64_decoded_bytes(s: str) -> int:
    """Estimate decoded byte length of a base64 string without decoding it."""
    s = (s or "").strip()
    if not s:
        return 0

    padding = 0
    if s.endswith("=="):
        padding = 2
    elif s.endswith("="):
        padding = 1

    # base64 expands 3 bytes -> 4 chars
    return max(0, (len(s) * 3) // 4 - padding)


class _TrackedAudioQueue(asyncio.Queue):
    """Track total audio samples currently buffered in vLLM's audio_queue."""

    def __init__(self) -> None:
        super().__init__()
        self.total_samples: int = 0

    @staticmethod
    def _count_samples(item: object) -> int:
        if item is None:
            return 0
        try:
            return int(len(item))  # np.ndarray -> num samples
        except Exception:
            return 0

    def put_nowait(self, item) -> None:  # type: ignore[override]
        self.total_samples += self._count_samples(item)
        super().put_nowait(item)

    async def put(self, item) -> None:  # type: ignore[override]
        self.total_samples += self._count_samples(item)
        await super().put(item)

    def get_nowait(self):  # type: ignore[override]
        item = super().get_nowait()
        self.total_samples -= self._count_samples(item)
        self.total_samples = max(0, int(self.total_samples))
        return item

    async def get(self):  # type: ignore[override]
        item = await super().get()
        self.total_samples -= self._count_samples(item)
        self.total_samples = max(0, int(self.total_samples))
        return item

    def backlog_seconds(self) -> float:
        return float(self.total_samples) / float(ASR_SAMPLE_RATE_HZ)

    def drop_oldest_to_max_backlog(self, *, max_backlog_seconds: float) -> float:
        if max_backlog_seconds <= 0:
            return 0.0

        dropped_samples = 0
        while not self.empty() and self.backlog_seconds() > float(max_backlog_seconds):
            try:
                item = super().get_nowait()
            except Exception:
                break
            if item is None:
                # Preserve sentinel used to end the stream.
                super().put_nowait(None)
                break
            dropped_samples += self._count_samples(item)
            self.total_samples -= self._count_samples(item)
            self.total_samples = max(0, int(self.total_samples))

        return float(dropped_samples) / float(ASR_SAMPLE_RATE_HZ)


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

        self._conn: RealtimeConnection | None = None
        self._send_ws: EnvelopeWebSocket | None = None

        # Inbound audio buffering/rolling state (per external request_id).
        self._audio_pending: deque[tuple[str, int]] = deque()  # (audio_b64, decoded_bytes_est)
        self._audio_pending_bytes: int = 0

        self._overlap_chunks: deque[tuple[str, int]] = deque()
        self._overlap_bytes: int = 0

        self._segment_bytes_sent: int = 0

        segment_target = int(max(1.0, float(STT_SEGMENT_SECONDS)) * _ASR_BYTES_PER_SECOND)
        # Even with rolling enabled, vLLM enforces max_model_len. Bound segment size so we
        # never hit the limit due to audio tokens.
        max_audio_tokens = max(1, int(VLLM_MAX_MODEL_LEN) - _AUDIO_TOKEN_HEADROOM)
        safe_max_audio_bytes = max_audio_tokens * _AUDIO_BYTES_PER_TOKEN
        self._segment_target_bytes = min(segment_target, safe_max_audio_bytes)
        self._overlap_target_bytes: int = int(max(0.0, float(STT_SEGMENT_OVERLAP_SECONDS)) * _ASR_BYTES_PER_SECOND)
        self._max_backlog_bytes: int = int(max(0.0, float(STT_MAX_BACKLOG_SECONDS)) * _ASR_BYTES_PER_SECOND)

        self._feed_event = asyncio.Event()
        self._feed_task: asyncio.Task | None = None

        self._utterance_active: bool = False
        self._finalize_requested: bool = False
        self._closing_segment: bool = False

        def _mark_disconnected() -> None:
            if self._conn is not None:
                try:
                    self._conn._is_connected = False
                except Exception:
                    return

        # vLLM expects a starlette-style WebSocket for sending; we wrap sends into envelopes.
        send_ws = EnvelopeWebSocket(ws, state, on_disconnect=_mark_disconnected)
        self._send_ws = send_ws

        self._conn = RealtimeConnection(send_ws, serving_realtime)
        # Swap in a tracked queue so we can implement "stay live" under overload
        # by dropping oldest unprocessed audio (Kyutai-like behavior).
        self._conn.audio_queue = _TrackedAudioQueue()
        # We run our own receive loop, so we mark the vLLM connection as active
        # (RealtimeConnection normally flips this in handle_connection()).
        self._conn._is_connected = True

        self._initialized = False

    async def ensure_initialized(self) -> None:
        if self._initialized:
            return
        await self.handle_event("session.update", {"model": self._allowed_model_name})
        self._initialized = True

    def _ensure_feed_task(self) -> None:
        if self._feed_task is None or self._feed_task.done():
            self._feed_task = asyncio.create_task(self._feed_loop())

    def _reset_audio_state(self) -> None:
        self._audio_pending.clear()
        self._audio_pending_bytes = 0
        self._overlap_chunks.clear()
        self._overlap_bytes = 0
        self._segment_bytes_sent = 0
        self._finalize_requested = False
        self._closing_segment = False

    def _push_overlap_chunk(self, audio_b64: str, decoded_bytes: int) -> None:
        if self._overlap_target_bytes <= 0 or decoded_bytes <= 0:
            return
        self._overlap_chunks.append((audio_b64, decoded_bytes))
        self._overlap_bytes += decoded_bytes
        while self._overlap_chunks and self._overlap_bytes > self._overlap_target_bytes:
            _old, old_bytes = self._overlap_chunks.popleft()
            self._overlap_bytes -= int(old_bytes)
        self._overlap_bytes = max(0, int(self._overlap_bytes))

    async def _await_generation_done(self, *, timeout_s: float = 60.0) -> None:
        if self._conn is None:
            return
        task = getattr(self._conn, "generation_task", None)
        if task is None:
            return
        if task.done():
            return
        await asyncio.wait_for(task, timeout=float(timeout_s))

    async def _commit_to_vllm(self, *, final: bool) -> None:
        if self._conn is None:
            raise RuntimeError("realtime connection is not initialized")
        await self._conn.handle_event({"type": "input_audio_buffer.commit", "final": bool(final)})

    async def _append_to_vllm(self, *, audio_b64: str) -> None:
        if self._conn is None:
            raise RuntimeError("realtime connection is not initialized")
        await self._conn.handle_event({"type": "input_audio_buffer.append", "audio": audio_b64})

        # Enforce a bounded audio backlog by dropping oldest unprocessed audio.
        q = getattr(self._conn, "audio_queue", None)
        if isinstance(q, _TrackedAudioQueue) and self._send_ws is not None:
            dropped_s = q.drop_oldest_to_max_backlog(max_backlog_seconds=float(STT_MAX_BACKLOG_SECONDS))
            if dropped_s > 0:
                await self._send_ws.send_status(
                    {
                        "kind": "overload_drop",
                        "dropped_seconds": float(dropped_s),
                        "max_backlog_seconds": float(STT_MAX_BACKLOG_SECONDS),
                        "source": "vllm_audio_queue",
                    }
                )

    async def _roll_segment(self) -> None:
        if not STT_INTERNAL_ROLL:
            return
        if self._conn is None:
            return
        if self._send_ws is None:
            return
        if self._finalize_requested:
            return
        if self._closing_segment:
            return

        self._closing_segment = True
        self._send_ws.suppress_next_done()

        # Finish current segment.
        await self._commit_to_vllm(final=True)
        await self._await_generation_done(timeout_s=120.0)

        # Start next segment.
        self._segment_bytes_sent = 0
        await self._commit_to_vllm(final=False)

        # Replay overlap first for boundary accuracy.
        for audio_b64, decoded_bytes in list(self._overlap_chunks):
            await self._append_to_vllm(audio_b64=audio_b64)
            self._segment_bytes_sent += int(decoded_bytes)

        self._closing_segment = False

    async def _finalize(self) -> None:
        if self._conn is None:
            return
        if self._send_ws is None:
            return
        if self._closing_segment:
            # If we're already closing, just wait for completion.
            await self._await_generation_done(timeout_s=120.0)
            self._utterance_active = False
            self._reset_audio_state()
            return

        await self._commit_to_vllm(final=True)
        await self._await_generation_done(timeout_s=120.0)
        self._utterance_active = False
        self._reset_audio_state()

    async def _feed_loop(self) -> None:
        while True:
            await self._feed_event.wait()
            self._feed_event.clear()

            if not self._utterance_active:
                continue

            try:
                # Drain pending audio into vLLM as fast as possible.
                while self._utterance_active and not self._closing_segment:
                    if self._audio_pending:
                        audio_b64, decoded_bytes = self._audio_pending.popleft()
                        self._audio_pending_bytes -= int(decoded_bytes)
                        self._audio_pending_bytes = max(0, int(self._audio_pending_bytes))

                        await self._append_to_vllm(audio_b64=audio_b64)
                        self._segment_bytes_sent += int(decoded_bytes)
                        self._push_overlap_chunk(audio_b64, int(decoded_bytes))

                        if (
                            STT_INTERNAL_ROLL
                            and not self._finalize_requested
                            and self._segment_target_bytes > 0
                            and self._segment_bytes_sent >= self._segment_target_bytes
                        ):
                            await self._roll_segment()
                        continue

                    if self._finalize_requested:
                        await self._finalize()
                        break

                    break
            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception("audio feeder failed")
                # Best-effort cleanup; connection will likely be cancelled by outer handlers.
                with contextlib.suppress(Exception):
                    await self.cancel()
                return

    async def handle_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "session.update":
            self._initialized = True
        event: dict[str, Any] = {"type": event_type}
        event.update(payload)
        if self._conn is None:
            raise RuntimeError("realtime connection is not initialized")

        if event_type == "input_audio_buffer.commit":
            final = bool(payload.get("final", False))
            if not final:
                # Start a new utterance and allow indefinite audio by rolling segments internally.
                self._reset_audio_state()
                self._utterance_active = True
                self._finalize_requested = False
                self._ensure_feed_task()
                await self._conn.handle_event(event)
            else:
                # Flush buffered audio then finalize (commit to vLLM happens in the feeder).
                self._finalize_requested = True
                self._ensure_feed_task()
                self._feed_event.set()
            return

        if event_type == "input_audio_buffer.append":
            audio_b64 = payload.get("audio")
            if isinstance(audio_b64, str) and audio_b64.strip():
                decoded_bytes = _estimate_b64_decoded_bytes(audio_b64)
                self._audio_pending.append((audio_b64, int(decoded_bytes)))
                self._audio_pending_bytes += int(decoded_bytes)

                if self._max_backlog_bytes > 0 and self._audio_pending_bytes > self._max_backlog_bytes:
                    dropped = 0
                    while self._audio_pending and self._audio_pending_bytes > self._max_backlog_bytes:
                        _old_b64, old_bytes = self._audio_pending.popleft()
                        self._audio_pending_bytes -= int(old_bytes)
                        dropped += int(old_bytes)
                    self._audio_pending_bytes = max(0, int(self._audio_pending_bytes))

                    if dropped > 0 and self._send_ws is not None:
                        dropped_s = float(dropped) / float(_ASR_BYTES_PER_SECOND)
                        await self._send_ws.send_status(
                            {
                                "kind": "overload_drop",
                                "dropped_seconds": dropped_s,
                                "max_backlog_seconds": float(STT_MAX_BACKLOG_SECONDS),
                                "source": "pending_buffer",
                            }
                        )

                self._ensure_feed_task()
                self._feed_event.set()
                return

            # Fall back to vLLM validation error behavior.
            await self._conn.handle_event(event)
            return

        await self._conn.handle_event(event)

    async def cancel(self) -> None:
        """Best-effort cancel current generation + clear buffers."""
        try:
            if self._conn is None:
                return

            if self._feed_task is not None:
                self._feed_task.cancel()
                with contextlib.suppress(Exception):
                    await self._feed_task
                self._feed_task = None

            self._utterance_active = False
            self._finalize_requested = False
            self._closing_segment = False
            self._reset_audio_state()

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
