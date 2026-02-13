"""Logging initialization."""

from __future__ import annotations

import os
import logging

from src.config.logging import ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL, DEFAULT_LOG_FORMAT


def configure_logging() -> None:
    level = (os.getenv(ENV_LOG_LEVEL) or DEFAULT_LOG_LEVEL).strip().upper()
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)


__all__ = ["configure_logging"]
