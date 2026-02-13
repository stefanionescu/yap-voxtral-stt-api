from __future__ import annotations

import time

import config


def record_conversation_timing(base, handler, session_start: float, last_signal_ts: float) -> None:
    session_end = time.perf_counter()
    base.session_elapsed_s = session_end - session_start

    final_recv_ts = getattr(handler, "final_recv_ts", config.DEFAULT_ZERO) or config.DEFAULT_ZERO
    if final_recv_ts:
        base.finish_elapsed_s = session_end - final_recv_ts
    elif last_signal_ts:
        base.finish_elapsed_s = session_end - last_signal_ts
    else:
        base.finish_elapsed_s = config.DEFAULT_ZERO


__all__ = ["record_conversation_timing"]
