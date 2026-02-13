"""Secrets configuration (env-resolved constants only)."""

from __future__ import annotations

import os

VOXTRAL_API_KEY: str = (os.getenv("VOXTRAL_API_KEY") or "").strip()

__all__ = [
    "VOXTRAL_API_KEY",
]
