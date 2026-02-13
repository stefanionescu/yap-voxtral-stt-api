"""WebSocket connection admission control."""

from __future__ import annotations

import asyncio
from typing import Any


class ConnectionManager:
    def __init__(self, *, max_connections: int) -> None:
        self._max = max(1, int(max_connections))
        self._lock = asyncio.Lock()
        self._active: set[int] = set()

    async def connect(self, ws: Any) -> bool:
        """Attempt to admit a websocket connection (without accepting it)."""
        key = id(ws)
        async with self._lock:
            if len(self._active) >= self._max:
                return False
            self._active.add(key)
            return True

    async def disconnect(self, ws: Any) -> None:
        key = id(ws)
        async with self._lock:
            self._active.discard(key)

    def get_connection_count(self) -> int:
        return len(self._active)


__all__ = ["ConnectionManager"]
