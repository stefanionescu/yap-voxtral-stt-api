from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HandlerSnapshot:
    final_text: str
    partial_ts: list[float]
    last_partial_ts: float
    first_delta_ts: float | None
    final_recv_ts: float
    error: str | None
    reject_reason: str | None


__all__ = ["HandlerSnapshot"]
