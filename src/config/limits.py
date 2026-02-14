"""Admission control configuration (env-resolved constants only)."""

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

__all__ = [
    "ASR_SAMPLE_RATE_HZ",
    "MAX_CONCURRENT_CONNECTIONS",
]
