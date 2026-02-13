"""Simple sliding-window rate limiter helpers."""

from __future__ import annotations

import time
import collections
from collections.abc import Callable

from src.errors import RateLimitError

TimeFn = Callable[[], float]


class SlidingWindowRateLimiter:
    """Track events over a rolling time window.

    Disabled if limit <= 0 or window_seconds <= 0.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        now_fn: TimeFn | None = None,
    ) -> None:
        self.limit = max(0, int(limit))
        self.window_seconds = max(0.0, float(window_seconds))
        self._now = now_fn or time.monotonic
        self._events: collections.deque[float] = collections.deque()
        self._enabled = self.limit > 0 and self.window_seconds > 0

    def consume(self) -> None:
        if not self._enabled:
            return

        now = self._now()
        cutoff = now - self.window_seconds

        events = self._events
        while events and events[0] <= cutoff:
            events.popleft()

        if len(events) >= self.limit:
            retry_in = (events[0] + self.window_seconds) - now
            raise RateLimitError(
                retry_in=max(0.0, retry_in),
                limit=self.limit,
                window_seconds=self.window_seconds,
            )

        events.append(now)


__all__ = ["RateLimitError", "SlidingWindowRateLimiter"]
