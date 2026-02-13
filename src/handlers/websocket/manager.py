"""Primary WebSocket connection handler orchestration."""

from __future__ import annotations

import logging
import contextlib

from fastapi import WebSocket

from src.runtime.dependencies import RuntimeDeps
from src.handlers.limits import SlidingWindowRateLimiter
from src.config.websocket import (
    WS_CLOSE_BUSY_CODE,
    WS_ERROR_AUTH_FAILED,
    WS_CLOSE_UNAUTHORIZED_CODE,
    WS_ERROR_SERVER_AT_CAPACITY,
)

from .errors import reject_connection
from .auth import authenticate_websocket
from .lifecycle import WebSocketLifecycle
from .message_loop import run_message_loop

logger = logging.getLogger(__name__)


def _create_rate_limiters(runtime_deps: RuntimeDeps) -> tuple[SlidingWindowRateLimiter, SlidingWindowRateLimiter]:
    message_limiter = SlidingWindowRateLimiter(
        limit=runtime_deps.settings.limits.ws_max_messages_per_window,
        window_seconds=runtime_deps.settings.limits.ws_message_window_seconds,
    )
    cancel_limiter = SlidingWindowRateLimiter(
        limit=runtime_deps.settings.limits.ws_max_cancels_per_window,
        window_seconds=runtime_deps.settings.limits.ws_cancel_window_seconds,
    )
    return message_limiter, cancel_limiter


async def _prepare_connection(ws: WebSocket, runtime_deps: RuntimeDeps) -> bool:
    if not await authenticate_websocket(ws, expected_api_key=runtime_deps.settings.auth.api_key):
        await reject_connection(
            ws,
            error_code=WS_ERROR_AUTH_FAILED,
            message=(
                "Authentication required. Provide valid API key via 'api_key' query parameter or 'X-API-Key' header."
            ),
            close_code=WS_CLOSE_UNAUTHORIZED_CODE,
        )
        return False

    if not await runtime_deps.connections.connect(ws):
        await reject_connection(
            ws,
            error_code=WS_ERROR_SERVER_AT_CAPACITY,
            message="Server cannot accept new connections. Please try again later.",
            close_code=WS_CLOSE_BUSY_CODE,
        )
        return False

    try:
        await ws.accept()
    except Exception:
        with contextlib.suppress(Exception):
            await runtime_deps.connections.disconnect(ws)
        raise
    return True


async def handle_websocket_connection(ws: WebSocket, runtime_deps: RuntimeDeps) -> None:
    lifecycle: WebSocketLifecycle | None = None
    admitted = False
    session_id: str | None = None
    try:
        if not await _prepare_connection(ws, runtime_deps):
            return
        admitted = True

        lifecycle = WebSocketLifecycle(
            ws,
            idle_timeout_s=runtime_deps.settings.websocket.idle_timeout_s,
            watchdog_tick_s=runtime_deps.settings.websocket.watchdog_tick_s,
            max_connection_duration_s=runtime_deps.settings.websocket.max_connection_duration_s,
        )
        lifecycle.start()

        message_limiter, cancel_limiter = _create_rate_limiters(runtime_deps)

        logger.info("WebSocket connection accepted. Active: %s", runtime_deps.connections.get_connection_count())
        session_id = await run_message_loop(ws, lifecycle, message_limiter, cancel_limiter, runtime_deps)
    finally:
        if lifecycle is not None:
            with contextlib.suppress(Exception):
                await lifecycle.stop()

        if admitted:
            with contextlib.suppress(Exception):
                await runtime_deps.connections.disconnect(ws)
            logger.info(
                "WebSocket connection closed session_id=%s. Active: %s",
                session_id,
                runtime_deps.connections.get_connection_count(),
            )


__all__ = ["handle_websocket_connection"]
