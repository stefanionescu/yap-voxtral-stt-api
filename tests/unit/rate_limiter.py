from __future__ import annotations

import pytest

from src.errors import RateLimitError
from src.handlers.limits import SlidingWindowRateLimiter


def test_rate_limiter_allows_within_limit() -> None:
    t = 0.0

    def now() -> float:
        return t

    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10, now_fn=now)
    limiter.consume()
    limiter.consume()


def test_rate_limiter_rejects_when_saturated() -> None:
    t = 0.0

    def now() -> float:
        return t

    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10, now_fn=now)
    limiter.consume()
    limiter.consume()

    with pytest.raises(RateLimitError) as exc:
        limiter.consume()
    assert exc.value.limit == 2
    assert exc.value.window_seconds == 10
