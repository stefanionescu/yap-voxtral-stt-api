from __future__ import annotations

import asyncio

import pytest

from src.handlers.websocket.lifecycle import WebSocketLifecycle
from src.config.websocket import WS_CLOSE_MAX_DURATION_CODE, WS_CLOSE_MAX_DURATION_REASON


class _FakeWebSocket:
    def __init__(self) -> None:
        self.closed = asyncio.Event()
        self.close_code: int | None = None
        self.close_reason: str | None = None

    async def close(self, *, code: int = 1000, reason: str | None = None) -> None:
        self.close_code = code
        self.close_reason = reason or ""
        self.closed.set()


@pytest.mark.asyncio
async def test_websocket_lifecycle_closes_on_max_duration() -> None:
    ws = _FakeWebSocket()
    lifecycle = WebSocketLifecycle(
        ws,
        idle_timeout_s=9999.0,
        watchdog_tick_s=0.01,
        max_connection_duration_s=0.05,
    )
    lifecycle.start()

    await asyncio.wait_for(ws.closed.wait(), timeout=1.0)
    assert ws.close_code == WS_CLOSE_MAX_DURATION_CODE
    assert ws.close_reason == WS_CLOSE_MAX_DURATION_REASON

    await lifecycle.stop()
