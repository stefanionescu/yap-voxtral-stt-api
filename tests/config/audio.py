"""Audio and sample defaults for client scripts."""

from __future__ import annotations

from .samples import FILE_EXTS, SAMPLES_DIR_NAME

# PCM16 mono @ 16kHz.
ASR_SAMPLE_RATE: int = 16000

# Voxtral realtime operates on an ~80ms step (12.5Hz). Use 80ms chunks by default.
CHUNK_MS: int = 80
FRAME_TIME_SEC: float = CHUNK_MS / 1000.0
CHUNK_SAMPLES: int = int(ASR_SAMPLE_RATE * FRAME_TIME_SEC)

# WAV/FFmpeg decode target sample rate for client-side conversion.
FFMPEG_DECODE_SR_16K: int = 16000

PCM16_MAX_VALUE: int = 32767

__all__ = [
    "ASR_SAMPLE_RATE",
    "CHUNK_MS",
    "CHUNK_SAMPLES",
    "FFMPEG_DECODE_SR_16K",
    "FILE_EXTS",
    "FRAME_TIME_SEC",
    "PCM16_MAX_VALUE",
    "SAMPLES_DIR_NAME",
]
