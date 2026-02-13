from __future__ import annotations

from tests.data.metrics import compute_stream_timeout_seconds


def compute_stream_timeout_seconds_for(audio_seconds: float) -> float:
    return compute_stream_timeout_seconds(audio_seconds, wait_for_ready=True)


__all__ = ["compute_stream_timeout_seconds_for"]
