"""Shared WebSocket client base with connection and protocol helpers."""

from __future__ import annotations

import json
import time
import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import websockets

from params import config
from utils.messages import MessageHandler
from utils.network import enable_tcp_nodelay

from .connection import build_url, get_ws_options
from .finalize import ensure_completion_and_close as _ensure_completion_and_close_fn
from .stream import create_streamer as _create_streamer_fn, stream_audio_with_callback as _stream_audio_with_callback_fn
from .timing import (
    wait_for_ready as _wait_for_ready_fn,
    reset_timing_metrics as _reset_timing_metrics_fn,
    record_session_timing as _record_session_timing_fn,
)

if TYPE_CHECKING:
    from utils.audio import AudioStreamer


class WSClientBase:
    """Core WebSocket client functionality shared by specialized clients."""

    def __init__(
        self,
        server: str,
        secure: bool = False,
        debug: bool = False,
    ) -> None:
        self.server = server
        self.secure = secure
        self.debug = debug
        self.url = build_url(server, secure)

        # Timing fields used by printing helpers.
        self.last_chunk_sent_ts: float = config.DEFAULT_ZERO
        self.connect_elapsed_s: float = config.DEFAULT_ZERO
        self.handshake_elapsed_s: float = config.DEFAULT_ZERO
        self.first_audio_sent_ts: float = config.DEFAULT_ZERO
        self.session_start_ts: float = config.DEFAULT_ZERO
        self.close_elapsed_s: float = config.DEFAULT_ZERO
        self.finish_elapsed_s: float = config.DEFAULT_ZERO
        self.session_elapsed_s: float = config.DEFAULT_ZERO

        _reset_timing_metrics_fn(self)

        self._messages_task: asyncio.Task | None = None

    def _reset_timing_metrics(self) -> None:
        _reset_timing_metrics_fn(self)

    @staticmethod
    def _get_auth_headers() -> list[tuple[str, str]]:
        return []

    def _get_ws_options(self) -> dict[str, Any]:
        return get_ws_options(self._get_auth_headers())

    async def _setup_connection(self, ws, handler: MessageHandler, session_start: float) -> None:
        self.connect_elapsed_s = time.perf_counter() - session_start
        enable_tcp_nodelay(ws)
        self._messages_task = asyncio.create_task(handler.process_messages(ws, session_start))
        handshake_elapsed = await _wait_for_ready_fn(handler, session_start)
        if handshake_elapsed is not None:
            self.handshake_elapsed_s = handshake_elapsed

    def _create_streamer(self, pcm_bytes: bytes) -> AudioStreamer:
        return _create_streamer_fn(pcm_bytes, self.debug)

    async def _stream_audio_with_callback(
        self,
        ws,
        streamer: AudioStreamer,
        handler: MessageHandler,
        *,
        session_id: str,
        request_id: str,
    ) -> float:
        return await _stream_audio_with_callback_fn(
            ws,
            streamer,
            handler,
            self,
            session_id=session_id,
            request_id=request_id,
        )

    async def _ensure_completion_and_close(
        self,
        handler: MessageHandler,
        ws,
        *,
        session_id: str,
        request_id: str,
        timeout_s: float,
    ) -> None:
        await _ensure_completion_and_close_fn(
            handler,
            ws,
            self,
            session_id=session_id,
            request_id=request_id,
            timeout_s=timeout_s,
        )

    def _record_session_timing(self, handler: MessageHandler, session_start: float, last_signal_ts: float) -> None:
        _record_session_timing_fn(self, handler, session_start, last_signal_ts)

    async def _process_stream(
        self,
        pcm_bytes: bytes,
        handler: MessageHandler,
        *,
        session_id: str,
        request_id: str,
        timeout_s: float,
    ) -> tuple[float, float]:
        self._reset_timing_metrics()
        ws_options = self._get_ws_options()
        session_start = time.perf_counter()
        self.session_start_ts = session_start

        async with websockets.connect(self.url, **ws_options) as ws:
            await self._setup_connection(ws, handler, session_start)

            if handler.done_event.is_set():
                return session_start, time.perf_counter()

            # Start utterance.
            await ws.send(
                json.dumps({
                    config.PROTO_KEY_TYPE: config.PROTO_TYPE_AUDIO_COMMIT,
                    config.PROTO_KEY_SESSION_ID: session_id,
                    config.PROTO_KEY_REQUEST_ID: request_id,
                    config.PROTO_KEY_PAYLOAD: {"final": False},
                })
            )

            streamer = self._create_streamer(pcm_bytes)
            _ = await self._stream_audio_with_callback(
                ws,
                streamer,
                handler,
                session_id=session_id,
                request_id=request_id,
            )

            # Finalize utterance and use the commit as the tail-latency barrier.
            await ws.send(
                json.dumps({
                    config.PROTO_KEY_TYPE: config.PROTO_TYPE_AUDIO_COMMIT,
                    config.PROTO_KEY_SESSION_ID: session_id,
                    config.PROTO_KEY_REQUEST_ID: request_id,
                    config.PROTO_KEY_PAYLOAD: {"final": True},
                })
            )
            last_signal_ts = time.perf_counter()

            await self._ensure_completion_and_close(
                handler,
                ws,
                session_id=session_id,
                request_id=request_id,
                timeout_s=timeout_s,
            )

            if self._messages_task is not None:
                self._messages_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await self._messages_task

        self._record_session_timing(handler, session_start, last_signal_ts)
        return session_start, last_signal_ts


__all__ = ["WSClientBase"]
