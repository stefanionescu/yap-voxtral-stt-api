"""Factories for bridging JSON envelopes to vLLM realtime sessions."""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket

from src.state import EnvelopeState

from .adapter import RealtimeConnectionAdapter


class RealtimeBridge:
    def __init__(self, *, serving_realtime: Any, allowed_model_name: str) -> None:
        self._serving_realtime = serving_realtime
        self._allowed_model_name = allowed_model_name

    def new_connection(self, ws: WebSocket, state: EnvelopeState) -> RealtimeConnectionAdapter:
        return RealtimeConnectionAdapter(
            ws=ws,
            state=state,
            serving_realtime=self._serving_realtime,
            allowed_model_name=self._allowed_model_name,
        )


__all__ = ["RealtimeBridge"]
