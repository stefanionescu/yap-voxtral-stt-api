"""Logging configuration (env-resolved constants only)."""

from __future__ import annotations

import os

LOG_LEVEL: str = (os.getenv("LOG_LEVEL") or "INFO").strip().upper() or "INFO"
LOG_FORMAT: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"

__all__ = [
    "LOG_FORMAT",
    "LOG_LEVEL",
]
