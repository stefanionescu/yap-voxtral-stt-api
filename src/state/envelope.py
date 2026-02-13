"""Per-connection state for wrapping realtime frames in a JSON envelope."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable


@dataclass(slots=True)
class EnvelopeState:
    session_id: str = "unknown"
    request_id: str = "unknown"
    active_request_id: str | None = None
    inflight_request_id: str | None = None
    active_request_audio_bytes: int = 0
    touch: Callable[[], None] | None = None


__all__ = ["EnvelopeState"]
