"""Timing metrics helpers for WebSocket client sessions."""

from __future__ import annotations

import time
import asyncio

from tests import config


def reset_timing_metrics(base) -> None:
    base.last_chunk_sent_ts = config.DEFAULT_ZERO
    base.connect_elapsed_s = config.DEFAULT_ZERO
    base.handshake_elapsed_s = config.DEFAULT_ZERO
    base.first_audio_sent_ts = config.DEFAULT_ZERO
    base.session_start_ts = config.DEFAULT_ZERO
    base.close_elapsed_s = config.DEFAULT_ZERO
    base.finish_elapsed_s = config.DEFAULT_ZERO
    base.session_elapsed_s = config.DEFAULT_ZERO


async def wait_for_ready(handler, session_start: float) -> float | None:
    try:
        async with asyncio.timeout(config.READY_WAIT_TIMEOUT_S):
            await handler.ready_event.wait()
    except TimeoutError:
        return None
    if getattr(handler, "ready_recv_ts", None) is not None:
        return handler.ready_recv_ts - session_start
    return None


def record_session_timing(base, handler, session_start: float, last_signal_ts: float) -> None:
    session_end = time.perf_counter()
    base.session_elapsed_s = session_end - session_start

    final_recv_ts = getattr(handler, "final_recv_ts", config.DEFAULT_ZERO) or config.DEFAULT_ZERO
    if final_recv_ts:
        base.finish_elapsed_s = session_end - final_recv_ts
    elif last_signal_ts:
        base.finish_elapsed_s = session_end - last_signal_ts
    else:
        base.finish_elapsed_s = config.DEFAULT_ZERO


__all__ = ["record_session_timing", "reset_timing_metrics", "wait_for_ready"]
