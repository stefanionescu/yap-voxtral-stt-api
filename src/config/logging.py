"""Logging configuration."""

from __future__ import annotations

import os
import logging


def configure_logging() -> None:
    level = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


__all__ = ["configure_logging"]
