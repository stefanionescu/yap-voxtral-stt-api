"""Rate limiting utilities for WebSocket message handling."""

from __future__ import annotations

import math
from typing import Any

from fastapi import WebSocket

from src.errors import RateLimitError
from src.config.websocket import WS_ERROR_RATE_LIMITED
from src.handlers.limits import SlidingWindowRateLimiter

from .errors import safe_send_envelope, build_error_payload


def select_rate_limiter(
    msg_type: str,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
) -> tuple[SlidingWindowRateLimiter | None, str]:
    if msg_type == "cancel":
        return cancel_limiter, "cancel"
    if msg_type in {"ping", "pong", "end"}:
        return None, ""
    return message_limiter, "message"


async def consume_limiter(
    ws: WebSocket,
    limiter: SlidingWindowRateLimiter,
    label: str,
    *,
    session_id: str,
    request_id: str,
) -> bool:
    try:
        limiter.consume()
    except RateLimitError as exc:
        retry_in = getattr(exc, "retry_in", 1.0)
        retry_in_s = int(max(1, math.ceil(float(retry_in)))) if retry_in else 1
        details: dict[str, Any] = {
            "retry_in": retry_in_s,
            "limit": limiter.limit,
            "window_seconds": int(limiter.window_seconds),
            "kind": label,
        }
        await safe_send_envelope(
            ws,
            msg_type="error",
            session_id=session_id,
            request_id=request_id,
            payload=build_error_payload(
                WS_ERROR_RATE_LIMITED,
                f"{label} rate limit: at most {limiter.limit} per {int(limiter.window_seconds)} seconds; "
                f"retry in {retry_in_s} seconds",
                details=details,
                reason_code=f"{label}_rate_limited",
            ),
        )
        return False
    return True


__all__ = ["select_rate_limiter", "consume_limiter"]
