"""Admission control and rate limit configuration (env-resolved constants only)."""

from __future__ import annotations

import os

# Server expects PCM16 audio at 16kHz (Voxtral realtime default).
ASR_SAMPLE_RATE_HZ: int = 16000

_MAX_CONCURRENT_CONNECTIONS_RAW = (os.getenv("MAX_CONCURRENT_CONNECTIONS") or "").strip()
try:
    MAX_CONCURRENT_CONNECTIONS: int = int(_MAX_CONCURRENT_CONNECTIONS_RAW) if _MAX_CONCURRENT_CONNECTIONS_RAW else 0
except Exception:
    MAX_CONCURRENT_CONNECTIONS = 0
MAX_CONCURRENT_CONNECTIONS = max(0, int(MAX_CONCURRENT_CONNECTIONS))

_WS_MESSAGE_WINDOW_SECONDS_RAW = (os.getenv("WS_MESSAGE_WINDOW_SECONDS") or "").strip()
try:
    WS_MESSAGE_WINDOW_SECONDS: float = float(_WS_MESSAGE_WINDOW_SECONDS_RAW) if _WS_MESSAGE_WINDOW_SECONDS_RAW else 60.0
except Exception:
    WS_MESSAGE_WINDOW_SECONDS = 60.0
if WS_MESSAGE_WINDOW_SECONDS <= 0:
    WS_MESSAGE_WINDOW_SECONDS = 60.0

# STT streaming is message-heavy. With 80ms chunks, clients send ~750 append messages/minute.
# Default high enough to support 20ms chunking (~3000/min) with headroom.
_WS_MAX_MESSAGES_PER_WINDOW_RAW = (os.getenv("WS_MAX_MESSAGES_PER_WINDOW") or "").strip()
try:
    WS_MAX_MESSAGES_PER_WINDOW: int = int(_WS_MAX_MESSAGES_PER_WINDOW_RAW) if _WS_MAX_MESSAGES_PER_WINDOW_RAW else 5000
except Exception:
    WS_MAX_MESSAGES_PER_WINDOW = 5000
WS_MAX_MESSAGES_PER_WINDOW = max(1, int(WS_MAX_MESSAGES_PER_WINDOW))

_WS_CANCEL_WINDOW_SECONDS_RAW = (os.getenv("WS_CANCEL_WINDOW_SECONDS") or "").strip()
try:
    WS_CANCEL_WINDOW_SECONDS: float = float(_WS_CANCEL_WINDOW_SECONDS_RAW) if _WS_CANCEL_WINDOW_SECONDS_RAW else 0.0
except Exception:
    WS_CANCEL_WINDOW_SECONDS = 0.0
if WS_CANCEL_WINDOW_SECONDS <= 0:
    WS_CANCEL_WINDOW_SECONDS = float(WS_MESSAGE_WINDOW_SECONDS)

_WS_MAX_CANCELS_PER_WINDOW_RAW = (os.getenv("WS_MAX_CANCELS_PER_WINDOW") or "").strip()
try:
    WS_MAX_CANCELS_PER_WINDOW: int = int(_WS_MAX_CANCELS_PER_WINDOW_RAW) if _WS_MAX_CANCELS_PER_WINDOW_RAW else 50
except Exception:
    WS_MAX_CANCELS_PER_WINDOW = 50
WS_MAX_CANCELS_PER_WINDOW = max(0, int(WS_MAX_CANCELS_PER_WINDOW))

__all__ = [
    "ASR_SAMPLE_RATE_HZ",
    "MAX_CONCURRENT_CONNECTIONS",
    "WS_CANCEL_WINDOW_SECONDS",
    "WS_MAX_CANCELS_PER_WINDOW",
    "WS_MAX_MESSAGES_PER_WINDOW",
    "WS_MESSAGE_WINDOW_SECONDS",
]
