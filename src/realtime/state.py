"""Per-connection state for wrapping vLLM realtime frames in a Yap envelope."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EnvelopeState:
    session_id: str = "unknown"
    request_id: str = "unknown"
    active_request_id: str | None = None


__all__ = ["EnvelopeState"]
