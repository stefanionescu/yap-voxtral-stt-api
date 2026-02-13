"""Model configuration (constants only)."""

from __future__ import annotations

from pathlib import Path

ENV_VOXTRAL_MODEL_ID = "VOXTRAL_MODEL_ID"
DEFAULT_VOXTRAL_MODEL_ID = "mistralai/Voxtral-Mini-4B-Realtime-2602"

# Served model name vLLM exposes to the realtime protocol ("model" in session.update).
ENV_VOXTRAL_SERVED_MODEL_NAME = "VOXTRAL_SERVED_MODEL_NAME"

# Voxtral Realtime: transcription_delay_ms must be a multiple of 80ms (80..2400).
ENV_VOXTRAL_TRANSCRIPTION_DELAY_MS = "VOXTRAL_TRANSCRIPTION_DELAY_MS"
DEFAULT_VOXTRAL_TRANSCRIPTION_DELAY_MS = 400

# Where we keep a writable snapshot of the model repo (for patching tekken.json).
ENV_VOXTRAL_MODEL_DIR = "VOXTRAL_MODEL_DIR"
DEFAULT_VOXTRAL_MODEL_DIR = Path("models") / "voxtral"

ENV_VOXTRAL_TEKKEN_FILENAME = "VOXTRAL_TEKKEN_FILENAME"
DEFAULT_VOXTRAL_TEKKEN_FILENAME = "tekken.json"

__all__ = [
    "DEFAULT_VOXTRAL_MODEL_DIR",
    "DEFAULT_VOXTRAL_MODEL_ID",
    "DEFAULT_VOXTRAL_TEKKEN_FILENAME",
    "DEFAULT_VOXTRAL_TRANSCRIPTION_DELAY_MS",
    "ENV_VOXTRAL_MODEL_DIR",
    "ENV_VOXTRAL_MODEL_ID",
    "ENV_VOXTRAL_SERVED_MODEL_NAME",
    "ENV_VOXTRAL_TEKKEN_FILENAME",
    "ENV_VOXTRAL_TRANSCRIPTION_DELAY_MS",
]
