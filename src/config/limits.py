"""Connection and rate-limit configuration."""

from __future__ import annotations

import os


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except Exception:
        return default


MAX_CONCURRENT_CONNECTIONS = _int_env("MAX_CONCURRENT_CONNECTIONS", 100)

WS_MESSAGE_WINDOW_SECONDS = _float_env("WS_MESSAGE_WINDOW_SECONDS", 60.0)
WS_MAX_MESSAGES_PER_WINDOW = _int_env("WS_MAX_MESSAGES_PER_WINDOW", 200)

WS_CANCEL_WINDOW_SECONDS = _float_env("WS_CANCEL_WINDOW_SECONDS", WS_MESSAGE_WINDOW_SECONDS)
WS_MAX_CANCELS_PER_WINDOW = _int_env("WS_MAX_CANCELS_PER_WINDOW", 50)

__all__ = [
    "MAX_CONCURRENT_CONNECTIONS",
    "WS_MESSAGE_WINDOW_SECONDS",
    "WS_MAX_MESSAGES_PER_WINDOW",
    "WS_CANCEL_WINDOW_SECONDS",
    "WS_MAX_CANCELS_PER_WINDOW",
]
