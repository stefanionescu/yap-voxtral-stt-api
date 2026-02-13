"""Logging initialization."""

from __future__ import annotations

import logging

from src.config.logging import LOG_LEVEL, LOG_FORMAT


def configure_logging() -> None:
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


__all__ = ["configure_logging"]
