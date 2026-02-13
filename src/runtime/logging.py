"""Logging initialization."""

from __future__ import annotations

import logging

from src.config.logging import LOG_LEVEL, LOG_FORMAT
from src.runtime.third_party_log_filters import configure as configure_third_party_log_filters


def configure_logging() -> None:
    configure_third_party_log_filters()
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


__all__ = ["configure_logging"]
