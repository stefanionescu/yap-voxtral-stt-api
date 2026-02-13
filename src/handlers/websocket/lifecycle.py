"""Per-connection WebSocket lifecycle helpers (idle enforcement)."""

from __future__ import annotations

import time
import asyncio
import logging
import contextlib

from fastapi import WebSocket

from src.config.websocket import (
    WS_IDLE_TIMEOUT_S,
    WS_CLOSE_IDLE_CODE,
    WS_WATCHDOG_TICK_S,
    WS_CLOSE_IDLE_REASON,
    WS_CLOSE_MAX_DURATION_CODE,
    WS_CLOSE_MAX_DURATION_REASON,
    WS_MAX_CONNECTION_DURATION_S,
)

logger = logging.getLogger(__name__)


class WebSocketLifecycle:
    def __init__(
        self,
        websocket: WebSocket,
        *,
        idle_timeout_s: float | None = None,
        watchdog_tick_s: float | None = None,
        max_connection_duration_s: float | None = None,
    ) -> None:
        self._ws = websocket
        self._idle_timeout_s = float(idle_timeout_s or WS_IDLE_TIMEOUT_S)
        self._watchdog_tick_s = float(watchdog_tick_s or WS_WATCHDOG_TICK_S)
        self._max_connection_duration_s = float(max_connection_duration_s or WS_MAX_CONNECTION_DURATION_S)
        self._connection_start = time.monotonic()
        self._last_activity = time.monotonic()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    def touch(self) -> None:
        self._last_activity = time.monotonic()

    def should_close(self) -> bool:
        return self._stop_event.is_set()

    def start(self) -> asyncio.Task:
        if self._task is None:
            self._task = asyncio.create_task(self._watchdog_loop())
        return self._task

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(Exception):
            await self._task
        self._task = None

    async def _watchdog_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self._watchdog_tick_s)
                if self._stop_event.is_set():
                    break
                if (time.monotonic() - self._connection_start) >= self._max_connection_duration_s:
                    logger.info("WebSocket max duration reached; closing connection")
                    self._stop_event.set()
                    with contextlib.suppress(Exception):
                        await self._ws.close(
                            code=WS_CLOSE_MAX_DURATION_CODE,
                            reason=WS_CLOSE_MAX_DURATION_REASON,
                        )
                    break
                if (time.monotonic() - self._last_activity) >= self._idle_timeout_s:
                    logger.info("WebSocket idle timeout reached; closing connection")
                    self._stop_event.set()
                    with contextlib.suppress(Exception):
                        await self._ws.close(code=WS_CLOSE_IDLE_CODE, reason=WS_CLOSE_IDLE_REASON)
                    break
        except asyncio.CancelledError:
            return
        except Exception:
            logger.debug("idle watchdog exiting due to unexpected error", exc_info=True)


__all__ = ["WebSocketLifecycle"]
