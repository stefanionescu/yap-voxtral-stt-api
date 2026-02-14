"""Realtime streaming settings (env-resolved constants only)."""

from __future__ import annotations

import os

_DISABLED_VALUES = {"0", "none", "null", "disabled", "disable", "off", "false"}


def _get_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)


def _get_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return bool(default)
    if raw in _DISABLED_VALUES:
        return False
    return raw in {"1", "true", "yes", "y", "on"}


# Internal rolling: keep vLLM requests bounded and "infinite" from the client POV.
STT_INTERNAL_ROLL: bool = _get_bool("STT_INTERNAL_ROLL", True)

# How many seconds of audio to send per internal segment before rolling.
STT_SEGMENT_SECONDS: float = max(1.0, _get_float("STT_SEGMENT_SECONDS", 60.0))

# How many seconds of audio to replay at the next segment start.
STT_SEGMENT_OVERLAP_SECONDS: float = max(0.0, _get_float("STT_SEGMENT_OVERLAP_SECONDS", 0.8))

# When inbound audio backlog exceeds this, drop oldest audio to stay live.
STT_MAX_BACKLOG_SECONDS: float = max(0.0, _get_float("STT_MAX_BACKLOG_SECONDS", 5.0))


__all__ = [
    "STT_INTERNAL_ROLL",
    "STT_MAX_BACKLOG_SECONDS",
    "STT_SEGMENT_OVERLAP_SECONDS",
    "STT_SEGMENT_SECONDS",
]

