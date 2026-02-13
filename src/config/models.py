"""Model selection and Voxtral-specific configuration."""

from __future__ import annotations

import os
from pathlib import Path

VOXTRAL_MODEL_ID = os.getenv("VOXTRAL_MODEL_ID", "mistralai/Voxtral-Mini-4B-Realtime-2602").strip()

# Served model name vLLM exposes to the realtime protocol ("model" in session.update).
VOXTRAL_SERVED_MODEL_NAME = os.getenv("VOXTRAL_SERVED_MODEL_NAME", VOXTRAL_MODEL_ID).strip()

# Voxtral Realtime: transcription_delay_ms must be a multiple of 80ms (80..2400).
VOXTRAL_TRANSCRIPTION_DELAY_MS = int(os.getenv("VOXTRAL_TRANSCRIPTION_DELAY_MS", "400"))

# Where we keep a writable snapshot of the model repo (for patching tekken.json).
_default_model_dir = Path("models") / "voxtral"
VOXTRAL_MODEL_DIR = Path(os.getenv("VOXTRAL_MODEL_DIR", str(_default_model_dir))).expanduser()

VOXTRAL_TEKKEN_FILENAME = os.getenv("VOXTRAL_TEKKEN_FILENAME", "tekken.json").strip()

__all__ = [
    "VOXTRAL_MODEL_ID",
    "VOXTRAL_SERVED_MODEL_NAME",
    "VOXTRAL_TRANSCRIPTION_DELAY_MS",
    "VOXTRAL_MODEL_DIR",
    "VOXTRAL_TEKKEN_FILENAME",
]
