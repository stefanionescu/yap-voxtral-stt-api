from __future__ import annotations

from tests import config
from tests.state.convo import HandlerSnapshot


def capture_handler_state(handler) -> HandlerSnapshot:
    return HandlerSnapshot(
        final_text=str(getattr(handler, "final_text", "")),
        partial_ts=list(getattr(handler, "partial_ts", [])),
        last_partial_ts=float(getattr(handler, "last_partial_ts", config.DEFAULT_ZERO)),
        first_delta_ts=getattr(handler, "first_delta_ts", None),
        final_recv_ts=float(getattr(handler, "final_recv_ts", config.DEFAULT_ZERO)),
        error=getattr(handler, "error", None),
        reject_reason=getattr(handler, "reject_reason", None),
    )


def reset_handler_for_next_segment(handler) -> None:
    handler.final_text = ""
    handler.partial_ts = []
    handler.last_partial_ts = config.DEFAULT_ZERO
    handler.first_delta_ts = None
    handler.final_recv_ts = config.DEFAULT_ZERO
    handler.error = None
    handler.reject_reason = None
    handler.done_event.clear()


__all__ = ["HandlerSnapshot", "capture_handler_state", "reset_handler_for_next_segment"]
