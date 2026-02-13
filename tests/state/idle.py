from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IdleTestResult:
    success: bool
    elapsed_s: float
    close_code: int | None = None
    close_reason: str | None = None
    error: str | None = None


__all__ = ["IdleTestResult"]
