"""WebSocket message loop for Voxtral Realtime (/api/asr-streaming)."""

from __future__ import annotations

import asyncio
import logging
import contextlib
from typing import Any, Literal

from fastapi import WebSocket, WebSocketDisconnect

from src.runtime.dependencies import RuntimeDeps
from src.handlers.limits import SlidingWindowRateLimiter
from src.realtime import EnvelopeState, RealtimeConnectionAdapter
from src.config.websocket import (
    WS_ERROR_INTERNAL,
    WS_CLOSE_BUSY_CODE,
    WS_ERROR_INVALID_MESSAGE,
    WS_CLOSE_CLIENT_REQUEST_CODE,
)

from .dispatch import HANDLERS
from .parser import parse_client_message
from .lifecycle import WebSocketLifecycle
from .errors import send_error, safe_send_envelope
from .limits import consume_limiter, select_rate_limiter

logger = logging.getLogger(__name__)


async def _recv_text_with_watchdog(
    ws: WebSocket,
    lifecycle: WebSocketLifecycle,
    *,
    watchdog_tick_s: float,
) -> tuple[str | None, bool]:
    try:
        message = await asyncio.wait_for(
            ws.receive_text(),
            timeout=max(1.0, float(watchdog_tick_s) * 2.0),
        )
        return message, False
    except TimeoutError:
        return None, lifecycle.should_close()


async def _handle_control_message(
    ws: WebSocket,
    msg_type: str,
    *,
    session_id: str,
    request_id: str,
) -> Literal["none", "continue", "close"]:
    if msg_type == "ping":
        await safe_send_envelope(ws, msg_type="pong", session_id=session_id, request_id=request_id, payload={})
        return "continue"
    if msg_type == "pong":
        return "continue"
    if msg_type == "end":
        await safe_send_envelope(ws, msg_type="session_end", session_id=session_id, request_id=request_id, payload={})
        with contextlib.suppress(Exception):
            await ws.close(code=WS_CLOSE_CLIENT_REQUEST_CODE)
        return "close"
    return "none"


async def _parse_or_send_error(ws: WebSocket, raw: str, state: EnvelopeState) -> dict[str, Any] | None:
    try:
        return parse_client_message(raw)
    except ValueError as exc:
        await send_error(
            ws,
            session_id=state.session_id,
            request_id=state.request_id,
            error_code=WS_ERROR_INVALID_MESSAGE,
            message=str(exc),
            reason_code="invalid_message",
        )
        return None


async def _inbound_processor_loop(
    ws: WebSocket,
    runtime_deps: RuntimeDeps,
    state: EnvelopeState,
    inbound_q: asyncio.Queue[dict[str, Any]],
    conn_box: dict[str, RealtimeConnectionAdapter | None],
) -> None:
    while True:
        msg = await inbound_q.get()
        msg_type = msg["type"]
        session_id = msg["session_id"]
        request_id = msg["request_id"]
        payload = msg["payload"] or {}

        state.session_id = session_id
        state.request_id = request_id

        handler = HANDLERS.get(msg_type)
        if handler is not None:
            conn_box["conn"] = await handler(
                ws,
                runtime_deps,
                state,
                conn_box["conn"],
                session_id,
                request_id,
                payload,
            )
            continue

        await send_error(
            ws,
            session_id=session_id,
            request_id=request_id,
            error_code=WS_ERROR_INVALID_MESSAGE,
            message=f"message type '{msg_type}' is not supported",
            reason_code="unknown_message_type",
        )


async def _receive_and_enqueue(
    ws: WebSocket,
    lifecycle: WebSocketLifecycle,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
    runtime_deps: RuntimeDeps,
    *,
    state: EnvelopeState,
    inbound_q: asyncio.Queue[dict[str, Any]],
) -> str | None:
    while True:
        raw, should_exit = await _recv_text_with_watchdog(
            ws,
            lifecycle,
            watchdog_tick_s=runtime_deps.settings.websocket.watchdog_tick_s,
        )
        if should_exit:
            return state.session_id if state.session_id != "unknown" else None
        if raw is None:
            continue

        lifecycle.touch()

        msg = await _parse_or_send_error(ws, raw, state)
        if msg is None:
            continue

        msg_type = msg["type"]
        session_id = msg["session_id"]
        request_id = msg["request_id"]

        state.session_id = session_id
        state.request_id = request_id

        limiter, label = select_rate_limiter(msg_type, message_limiter, cancel_limiter)
        if limiter is not None:
            ok = await consume_limiter(
                ws,
                limiter,
                label,
                session_id=session_id,
                request_id=request_id,
            )
            if not ok:
                continue

        control = await _handle_control_message(ws, msg_type, session_id=session_id, request_id=request_id)
        if control == "close":
            return session_id
        if control == "continue":
            continue

        try:
            inbound_q.put_nowait(msg)
        except asyncio.QueueFull:
            await send_error(
                ws,
                session_id=session_id,
                request_id=request_id,
                error_code=WS_ERROR_INTERNAL,
                message="server overloaded (inbound queue full)",
                reason_code="inbound_queue_full",
                details={"inbound_queue_max": inbound_q.maxsize},
            )
            with contextlib.suppress(Exception):
                await ws.close(code=WS_CLOSE_BUSY_CODE)
            return session_id


async def run_message_loop(
    ws: WebSocket,
    lifecycle: WebSocketLifecycle,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
    runtime_deps: RuntimeDeps,
) -> str | None:
    state = EnvelopeState()
    inbound_q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
        maxsize=max(1, int(runtime_deps.settings.websocket.inbound_queue_max))
    )
    conn_box: dict[str, RealtimeConnectionAdapter | None] = {"conn": None}

    processor_task: asyncio.Task | None = None
    try:
        processor_task = asyncio.create_task(_inbound_processor_loop(ws, runtime_deps, state, inbound_q, conn_box))
        return await _receive_and_enqueue(
            ws,
            lifecycle,
            message_limiter,
            cancel_limiter,
            runtime_deps,
            state=state,
            inbound_q=inbound_q,
        )
    except WebSocketDisconnect:
        return state.session_id if state.session_id != "unknown" else None
    finally:
        if processor_task is not None:
            with contextlib.suppress(BaseException):
                processor_task.cancel()
            with contextlib.suppress(BaseException):
                await processor_task
        if conn_box["conn"] is not None:
            with contextlib.suppress(Exception):
                await conn_box["conn"].cancel()


__all__ = ["run_message_loop"]
