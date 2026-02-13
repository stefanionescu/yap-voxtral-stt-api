"""Shared error types for the Voxtral STT server."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitError(Exception):
    """Raised when a sliding-window rate limiter is saturated."""

    retry_in: float
    limit: int
    window_seconds: float


__all__ = ["RateLimitError"]
