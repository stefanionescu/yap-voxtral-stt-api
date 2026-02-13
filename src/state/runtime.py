"""Typed runtime state objects for dependency wiring."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.state.settings import AppSettings
    from src.realtime.bridge import RealtimeBridge
    from src.handlers.connections import ConnectionManager


@dataclass(slots=True)
class RuntimeDeps:
    connections: ConnectionManager
    realtime_bridge: RealtimeBridge
    settings: AppSettings
    _engine_stack: Any

    async def shutdown(self) -> None:
        try:
            await self._engine_stack.aclose()
        except Exception:
            logger.exception("runtime shutdown failed")


__all__ = ["RuntimeDeps"]
