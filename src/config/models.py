"""Model configuration (env-resolved constants only)."""

from __future__ import annotations

import os
from pathlib import Path

_DELAY_MIN_MS = 80
_DELAY_MAX_MS = 2400
_DELAY_STEP_MS = 80

VOXTRAL_MODEL_ID: str = (os.getenv("VOXTRAL_MODEL_ID") or "").strip() or "mistralai/Voxtral-Mini-4B-Realtime-2602"

# Served model name vLLM exposes to the realtime protocol ("model" in session.update).
VOXTRAL_SERVED_MODEL_NAME: str = (os.getenv("VOXTRAL_SERVED_MODEL_NAME") or "").strip() or VOXTRAL_MODEL_ID

# Voxtral Realtime: transcription_delay_ms must be a multiple of 80ms (80..2400).
_DELAY_RAW = (os.getenv("VOXTRAL_TRANSCRIPTION_DELAY_MS") or "").strip()
try:
    VOXTRAL_TRANSCRIPTION_DELAY_MS: int = int(_DELAY_RAW) if _DELAY_RAW else 400
except Exception:
    VOXTRAL_TRANSCRIPTION_DELAY_MS = 400

if (
    VOXTRAL_TRANSCRIPTION_DELAY_MS < _DELAY_MIN_MS
    or VOXTRAL_TRANSCRIPTION_DELAY_MS > _DELAY_MAX_MS
    or (VOXTRAL_TRANSCRIPTION_DELAY_MS % _DELAY_STEP_MS) != 0
):
    raise ValueError(
        f"VOXTRAL_TRANSCRIPTION_DELAY_MS must be a multiple of {_DELAY_STEP_MS} between {_DELAY_MIN_MS} and"
        f" {_DELAY_MAX_MS}"
    )

# Where we keep a writable snapshot of the model repo (for patching tekken.json).
_MODEL_DIR_RAW = (os.getenv("VOXTRAL_MODEL_DIR") or "").strip()
VOXTRAL_MODEL_DIR: Path = Path(_MODEL_DIR_RAW).expanduser() if _MODEL_DIR_RAW else (Path("models") / "voxtral")

VOXTRAL_TEKKEN_FILENAME: str = (os.getenv("VOXTRAL_TEKKEN_FILENAME") or "").strip() or "tekken.json"

__all__ = [
    "VOXTRAL_MODEL_DIR",
    "VOXTRAL_MODEL_ID",
    "VOXTRAL_SERVED_MODEL_NAME",
    "VOXTRAL_TEKKEN_FILENAME",
    "VOXTRAL_TRANSCRIPTION_DELAY_MS",
]
