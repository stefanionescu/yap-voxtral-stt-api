"""Two-segment conversation client over a single WebSocket connection."""

from __future__ import annotations

import time
import uuid
import asyncio
from contextlib import suppress

import websockets

from utils.messages import MessageHandler
from utils.network import enable_tcp_nodelay
from data.metrics import compute_stream_timeout_seconds
from client.shared.connection import build_url, get_ws_options
from client.shared.timing import wait_for_ready, reset_timing_metrics

from .timing import record_conversation_timing
from .segment import process_conversation_segment
from .finalize import wait_for_done, close_ws_gracefully
from .result import build_conversation_result, calculate_segment_metrics
from .state import capture_handler_state, reset_handler_for_next_segment


class ConvoClient:
    def __init__(self, server: str, secure: bool = False, debug: bool = False) -> None:
        self.server = server
        self.secure = secure
        self.debug = debug

        self.url = build_url(server, secure)

        reset_timing_metrics(self)

        self._messages_task: asyncio.Task | None = None

    async def run_convo(
        self,
        pcm1: bytes,
        dur1_s: float,
        pcm2: bytes,
        dur2_s: float,
        pause_s: float,
        *,
        debug: bool = False,
    ) -> dict:
        ws_options = get_ws_options([])
        session_start = time.perf_counter()
        self.session_start_ts = session_start

        session_id = f"convo-{uuid.uuid4()}"
        req1 = f"utt-1-{uuid.uuid4()}"
        req2 = f"utt-2-{uuid.uuid4()}"

        handler = MessageHandler(debug=debug)

        async with websockets.connect(self.url, **ws_options) as ws:
            self.connect_elapsed_s = time.perf_counter() - session_start
            enable_tcp_nodelay(ws)
            self._messages_task = asyncio.create_task(handler.process_messages(ws, session_start))

            handshake_elapsed = await wait_for_ready(handler, session_start)
            if handshake_elapsed is not None:
                self.handshake_elapsed_s = handshake_elapsed

            # Segment 1
            seg1_results = await process_conversation_segment(
                self,
                ws,
                pcm1,
                session_id=session_id,
                request_id=req1,
                handler=handler,
                debug=debug,
            )
            await wait_for_done(
                handler,
                ws,
                session_id=session_id,
                request_id=req1,
                timeout_s=compute_stream_timeout_seconds(dur1_s, wait_for_ready=False),
            )

            seg1_ttfw_s = None
            if handler.first_delta_ts is not None and seg1_results.get("first_audio_sent_ts"):
                seg1_ttfw_s = float(handler.first_delta_ts - seg1_results["first_audio_sent_ts"])

            seg1_handler = capture_handler_state(handler)

            # Reset handler between segments
            reset_handler_for_next_segment(handler)

            # Pause locally between segments (do not send silence)
            if pause_s and pause_s > 0:
                await asyncio.sleep(float(pause_s))

            # Segment 2
            seg2_start = time.perf_counter()
            seg2_results = await process_conversation_segment(
                self,
                ws,
                pcm2,
                session_id=session_id,
                request_id=req2,
                handler=handler,
                debug=debug,
            )
            await wait_for_done(
                handler,
                ws,
                session_id=session_id,
                request_id=req2,
                timeout_s=compute_stream_timeout_seconds(dur2_s, wait_for_ready=False),
            )

            seg2_ttfw_s = None
            if handler.first_delta_ts is not None and seg2_results.get("first_audio_sent_ts"):
                seg2_ttfw_s = float(handler.first_delta_ts - seg2_results["first_audio_sent_ts"])

            await close_ws_gracefully(ws, self)

            if self._messages_task is not None:
                self._messages_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await self._messages_task

        record_conversation_timing(self, handler, session_start, float(seg2_results["last_signal_ts"]))

        return build_conversation_result(
            seg1_handler,
            handler,
            calculate_segment_metrics(seg1_handler, seg1_results, session_start, dur1_s),
            calculate_segment_metrics(handler, seg2_results, seg2_start, dur2_s),
            dur1_s,
            dur2_s,
            seg1_ttfw_s=seg1_ttfw_s,
            seg2_ttfw_s=seg2_ttfw_s,
        )


__all__ = ["ConvoClient"]
