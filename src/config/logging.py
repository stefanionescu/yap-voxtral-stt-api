"""Logging configuration (constants only)."""

from __future__ import annotations

ENV_LOG_LEVEL = "LOG_LEVEL"

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

__all__ = [
    "DEFAULT_LOG_FORMAT",
    "DEFAULT_LOG_LEVEL",
    "ENV_LOG_LEVEL",
]
