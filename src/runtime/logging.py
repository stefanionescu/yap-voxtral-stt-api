"""Logging initialization."""

from __future__ import annotations

import os
import logging

from src.config.logging import LOG_LEVEL, LOG_FORMAT


def configure_logging() -> None:
    # vLLM can be noisy at import/startup. Keep it tame unless explicitly enabled.
    if (os.getenv("SHOW_VLLM_LOGS") or "").strip().lower() not in {"1", "true", "yes"}:
        logging.getLogger("vllm").setLevel(logging.WARNING)
        logging.getLogger("vllm.entrypoints").setLevel(logging.WARNING)
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


__all__ = ["configure_logging"]
