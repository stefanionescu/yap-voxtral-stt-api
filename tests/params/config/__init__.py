"""Shared test client configuration."""

from __future__ import annotations

from .defaults import MS_PER_S, DEFAULT_TIMEOUT_S
from .websocket import WS_PING_TIMEOUT_S, WS_PING_INTERVAL_S
from .audio import (
    CHUNK_MS,
    FILE_EXTS,
    CHUNK_SAMPLES,
    ASR_SAMPLE_RATE,
    SAMPLES_DIR_NAME,
    FFMPEG_DECODE_SR_16K,
)

__all__ = [
    "MS_PER_S",
    "DEFAULT_TIMEOUT_S",
    "ASR_SAMPLE_RATE",
    "CHUNK_MS",
    "CHUNK_SAMPLES",
    "FFMPEG_DECODE_SR_16K",
    "SAMPLES_DIR_NAME",
    "FILE_EXTS",
    "WS_PING_INTERVAL_S",
    "WS_PING_TIMEOUT_S",
]
