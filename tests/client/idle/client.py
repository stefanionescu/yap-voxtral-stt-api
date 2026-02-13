"""Idle timeout test client.

Opens a WebSocket connection and waits for server-initiated close due to idle timeout.
"""

from __future__ import annotations

import time
import asyncio
import logging
from dataclasses import dataclass

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from utils.network import enable_tcp_nodelay
from client.shared.connection import build_url, get_ws_options

logger = logging.getLogger(__name__)


@dataclass
class IdleTestResult:
    success: bool
    elapsed_s: float
    close_code: int | None = None
    close_reason: str | None = None
    error: str | None = None


class IdleClient:
    def __init__(self, server: str, secure: bool = False, debug: bool = False):
        self.server = server
        self.secure = secure
        self.debug = debug
        self.url = build_url(server, secure)

    @staticmethod
    def _get_auth_headers() -> list[tuple[str, str]]:
        return []

    def _get_ws_options(self) -> dict:
        base_opts = get_ws_options(self._get_auth_headers())
        # Disable protocol-level ping/pong to let server detect idle client.
        base_opts["ping_interval"] = None
        base_opts["ping_timeout"] = None
        return base_opts

    async def run(self, timeout_s: float) -> IdleTestResult:
        ws_options = self._get_ws_options()
        start_time = time.perf_counter()

        try:
            async with websockets.connect(self.url, **ws_options) as ws:
                enable_tcp_nodelay(ws)
                if self.debug:
                    logger.debug("Connection established, waiting for server idle close...")

                try:
                    await asyncio.wait_for(self._wait_for_close(ws), timeout=timeout_s)
                    elapsed = time.perf_counter() - start_time
                    return IdleTestResult(
                        success=True,
                        elapsed_s=elapsed,
                        close_code=ws.close_code,
                        close_reason=ws.close_reason,
                    )
                except TimeoutError:
                    elapsed = time.perf_counter() - start_time
                    return IdleTestResult(
                        success=False,
                        elapsed_s=elapsed,
                        error=f"Server did not close connection within {timeout_s:.1f}s",
                    )

        except ConnectionClosedOK as exc:
            elapsed = time.perf_counter() - start_time
            return IdleTestResult(success=True, elapsed_s=elapsed, close_code=exc.code, close_reason=exc.reason)
        except ConnectionClosedError as exc:
            elapsed = time.perf_counter() - start_time
            return IdleTestResult(success=True, elapsed_s=elapsed, close_code=exc.code, close_reason=exc.reason)
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            return IdleTestResult(success=False, elapsed_s=elapsed, error=str(exc))

    async def _wait_for_close(self, ws) -> None:
        try:
            async for _ in ws:
                if self.debug:
                    logger.debug("Received message while waiting for close")
        except (ConnectionClosedOK, ConnectionClosedError):
            pass


__all__ = ["IdleClient", "IdleTestResult"]
