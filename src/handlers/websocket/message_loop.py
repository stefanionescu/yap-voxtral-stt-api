"""WebSocket message loop and dispatch for Voxtral Realtime (/ws)."""

from __future__ import annotations

import asyncio
import logging
import contextlib
from typing import Any
from typing import Literal
from collections.abc import Callable, Awaitable

from fastapi import WebSocket, WebSocketDisconnect

from src.runtime.dependencies import RuntimeDeps
from src.config.models import VOXTRAL_SERVED_MODEL_NAME
from src.handlers.limits import SlidingWindowRateLimiter
from src.realtime import EnvelopeState, RealtimeConnectionAdapter
from src.config.websocket import (
    WS_WATCHDOG_TICK_S,
    WS_ERROR_INVALID_MESSAGE,
    WS_ERROR_INVALID_PAYLOAD,
    WS_CLOSE_CLIENT_REQUEST_CODE,
)

from .parser import parse_client_message
from .lifecycle import WebSocketLifecycle
from .errors import send_error, safe_send_envelope
from .limits import consume_limiter, select_rate_limiter

logger = logging.getLogger(__name__)

HandlerFn = Callable[
    [WebSocket, RuntimeDeps, EnvelopeState, RealtimeConnectionAdapter | None, str, str, dict[str, Any]],
    Awaitable[RealtimeConnectionAdapter | None],
]


async def _recv_text_with_watchdog(ws: WebSocket, lifecycle: WebSocketLifecycle) -> tuple[str | None, bool]:
    try:
        message = await asyncio.wait_for(
            ws.receive_text(),
            timeout=WS_WATCHDOG_TICK_S * 2,
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


async def _ensure_connection(
    conn: RealtimeConnectionAdapter | None,
    *,
    runtime_deps: RuntimeDeps,
    ws: WebSocket,
    state: EnvelopeState,
    initialize: bool,
) -> RealtimeConnectionAdapter:
    if conn is None:
        conn = runtime_deps.realtime_bridge.new_connection(ws, state)
    if initialize:
        await conn.ensure_initialized()
    return conn


async def _handle_cancel(
    ws: WebSocket,
    _runtime_deps: RuntimeDeps,
    state: EnvelopeState,
    conn: RealtimeConnectionAdapter | None,
    session_id: str,
    request_id: str,
    payload: dict[str, Any],
) -> RealtimeConnectionAdapter | None:
    if conn is not None:
        await conn.cancel()
    state.active_request_id = None
    await safe_send_envelope(
        ws,
        msg_type="cancelled",
        session_id=session_id,
        request_id=request_id,
        payload={"reason": (payload.get("reason") or "client_request")},
    )
    return conn


async def _handle_session_update(
    ws: WebSocket,
    runtime_deps: RuntimeDeps,
    state: EnvelopeState,
    conn: RealtimeConnectionAdapter | None,
    session_id: str,
    request_id: str,
    payload: dict[str, Any],
) -> RealtimeConnectionAdapter | None:
    desired = (
        (payload.get("model") or VOXTRAL_SERVED_MODEL_NAME).strip()
        if isinstance(payload.get("model"), str)
        else VOXTRAL_SERVED_MODEL_NAME
    )
    if desired != VOXTRAL_SERVED_MODEL_NAME:
        await send_error(
            ws,
            session_id=session_id,
            request_id=request_id,
            error_code=WS_ERROR_INVALID_PAYLOAD,
            message="unsupported model",
            reason_code="unsupported_model",
            details={"allowed_model": VOXTRAL_SERVED_MODEL_NAME, "requested": desired},
        )
        return conn

    conn = await _ensure_connection(conn, runtime_deps=runtime_deps, ws=ws, state=state, initialize=False)
    await conn.handle_event("session.update", {"model": VOXTRAL_SERVED_MODEL_NAME})
    return conn


async def _handle_commit(
    ws: WebSocket,
    runtime_deps: RuntimeDeps,
    state: EnvelopeState,
    conn: RealtimeConnectionAdapter | None,
    session_id: str,
    request_id: str,
    payload: dict[str, Any],
) -> RealtimeConnectionAdapter | None:
    final = bool(payload.get("final", False))

    if not final:
        conn = await _ensure_connection(conn, runtime_deps=runtime_deps, ws=ws, state=state, initialize=True)
        # New utterance (non-final commit) cancels any previous active request on this connection.
        if state.active_request_id and state.active_request_id != request_id:
            await conn.cancel()
        state.active_request_id = request_id
    else:
        if state.active_request_id is None:
            await send_error(
                ws,
                session_id=session_id,
                request_id=request_id,
                error_code=WS_ERROR_INVALID_PAYLOAD,
                message="no active request; send input_audio_buffer.commit with final=false first",
                reason_code="no_active_request",
            )
            return conn
        if state.active_request_id != request_id:
            await send_error(
                ws,
                session_id=session_id,
                request_id=request_id,
                error_code=WS_ERROR_INVALID_PAYLOAD,
                message="request_id does not match active request",
                reason_code="request_id_mismatch",
                details={"active_request_id": state.active_request_id},
            )
            return conn
        conn = await _ensure_connection(conn, runtime_deps=runtime_deps, ws=ws, state=state, initialize=True)

    if conn is None:
        raise RuntimeError("internal error: realtime connection is missing after commit validation")

    await conn.handle_event("input_audio_buffer.commit", {"final": final})
    if final:
        state.active_request_id = None
    return conn


async def _handle_append(
    ws: WebSocket,
    runtime_deps: RuntimeDeps,
    state: EnvelopeState,
    conn: RealtimeConnectionAdapter | None,
    session_id: str,
    request_id: str,
    payload: dict[str, Any],
) -> RealtimeConnectionAdapter | None:
    audio = payload.get("audio")
    if not isinstance(audio, str) or not audio.strip():
        await send_error(
            ws,
            session_id=session_id,
            request_id=request_id,
            error_code=WS_ERROR_INVALID_PAYLOAD,
            message="payload.audio (base64 pcm16) is required",
            reason_code="missing_audio",
        )
        return conn

    if state.active_request_id is None or state.active_request_id != request_id:
        await send_error(
            ws,
            session_id=session_id,
            request_id=request_id,
            error_code=WS_ERROR_INVALID_PAYLOAD,
            message="no active request; send input_audio_buffer.commit final=false first",
            reason_code="no_active_request",
        )
        return conn

    conn = await _ensure_connection(conn, runtime_deps=runtime_deps, ws=ws, state=state, initialize=True)
    await conn.handle_event("input_audio_buffer.append", {"audio": audio})
    return conn


HANDLERS: dict[str, HandlerFn] = {
    "cancel": _handle_cancel,
    "session.update": _handle_session_update,
    "input_audio_buffer.commit": _handle_commit,
    "input_audio_buffer.append": _handle_append,
}


async def run_message_loop(
    ws: WebSocket,
    lifecycle: WebSocketLifecycle,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
    runtime_deps: RuntimeDeps,
) -> str | None:
    state = EnvelopeState()
    conn: RealtimeConnectionAdapter | None = None

    try:
        while True:
            raw, should_exit = await _recv_text_with_watchdog(ws, lifecycle)
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
            payload = msg["payload"] or {}

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

            handler = HANDLERS.get(msg_type)
            if handler is not None:
                conn = await handler(ws, runtime_deps, state, conn, session_id, request_id, payload)
                continue

            await send_error(
                ws,
                session_id=session_id,
                request_id=request_id,
                error_code=WS_ERROR_INVALID_MESSAGE,
                message=f"message type '{msg_type}' is not supported",
                reason_code="unknown_message_type",
            )
    except WebSocketDisconnect:
        return state.session_id if state.session_id != "unknown" else None
    finally:
        if conn is not None:
            with contextlib.suppress(Exception):
                await conn.cancel()


__all__ = ["run_message_loop"]
