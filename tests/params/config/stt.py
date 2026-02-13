from __future__ import annotations

# Default configured transcription delay on the server (seconds).
STT_DELAY_SEC: float = 0.4

# Approximate model step.
SERVER_STEP_MS: float = 80.0
SERVER_STEP_SEC: float = SERVER_STEP_MS / 1000.0

__all__ = ["SERVER_STEP_MS", "SERVER_STEP_SEC", "STT_DELAY_SEC"]
