"""Dispatch handlers for WebSocket JSON envelope messages."""

from __future__ import annotations

from typing import Any
from collections.abc import Callable, Awaitable

from fastapi import WebSocket

from src.runtime.dependencies import RuntimeDeps
from src.realtime import EnvelopeState, RealtimeConnectionAdapter
from src.config.websocket import WS_ERROR_INVALID_PAYLOAD, WS_ERROR_UTTERANCE_TOO_LONG
from src.config.limits import ASR_SAMPLE_RATE_HZ, MAX_UTTERANCE_AUDIO_BYTES, MAX_UTTERANCE_AUDIO_SECONDS

from .errors import send_error, safe_send_envelope

HandlerFn = Callable[
    [WebSocket, RuntimeDeps, EnvelopeState, RealtimeConnectionAdapter | None, str, str, dict[str, Any]],
    Awaitable[RealtimeConnectionAdapter | None],
]


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
    state.inflight_request_id = None
    state.active_request_audio_bytes = 0
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
    allowed_model_name = runtime_deps.settings.model.served_model_name
    desired = (
        (payload.get("model") or allowed_model_name).strip()
        if isinstance(payload.get("model"), str)
        else allowed_model_name
    )
    if desired != allowed_model_name:
        await send_error(
            ws,
            session_id=session_id,
            request_id=request_id,
            error_code=WS_ERROR_INVALID_PAYLOAD,
            message="unsupported model",
            reason_code="unsupported_model",
            details={"allowed_model": allowed_model_name, "requested": desired},
        )
        return conn

    conn = await _ensure_connection(conn, runtime_deps=runtime_deps, ws=ws, state=state, initialize=False)
    await conn.handle_event("session.update", {"model": allowed_model_name})
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
        if state.inflight_request_id and state.inflight_request_id != request_id:
            await conn.cancel()
            state.inflight_request_id = None
        if state.active_request_id and state.active_request_id != request_id:
            await conn.cancel()
            state.inflight_request_id = None
        state.active_request_id = request_id
        state.active_request_audio_bytes = 0
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

    if final:
        state.inflight_request_id = request_id
    await conn.handle_event("input_audio_buffer.commit", {"final": final})
    if final:
        state.active_request_id = None
        state.active_request_audio_bytes = 0
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

    if MAX_UTTERANCE_AUDIO_BYTES > 0:
        state.active_request_audio_bytes += _estimate_b64_decoded_bytes(audio)
        if state.active_request_audio_bytes > MAX_UTTERANCE_AUDIO_BYTES:
            received_s = state.active_request_audio_bytes / (ASR_SAMPLE_RATE_HZ * 2)
            await send_error(
                ws,
                session_id=session_id,
                request_id=request_id,
                error_code=WS_ERROR_UTTERANCE_TOO_LONG,
                message="utterance exceeded maximum audio duration; finalize or start a new request",
                reason_code="utterance_too_long",
                details={
                    "max_audio_seconds": float(MAX_UTTERANCE_AUDIO_SECONDS),
                    "max_audio_bytes": int(MAX_UTTERANCE_AUDIO_BYTES),
                    "received_audio_seconds": float(received_s),
                    "received_audio_bytes": int(state.active_request_audio_bytes),
                },
            )
            if conn is not None:
                await conn.cancel()
            state.active_request_id = None
            state.inflight_request_id = None
            state.active_request_audio_bytes = 0
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

__all__ = ["HANDLERS"]
