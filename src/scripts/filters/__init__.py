"""Log noise filters for third-party libraries.

This repo keeps the filter layer intentionally small: it only adjusts a few
environment variables and logger levels to keep startup logs readable.
"""

from __future__ import annotations

import os
import logging


def configure() -> None:
    # vLLM can be verbose at import/startup. Keep it tame unless explicitly enabled.
    if (os.getenv("SHOW_VLLM_LOGS") or "").strip() not in {"1", "true", "yes"}:
        logging.getLogger("vllm").setLevel(logging.WARNING)
        logging.getLogger("vllm.entrypoints").setLevel(logging.WARNING)

    # Avoid expensive compilation cache by default (Voxtral card suggests disabling).
    os.environ.setdefault("VLLM_DISABLE_COMPILE_CACHE", os.getenv("VLLM_DISABLE_COMPILE_CACHE", "1"))


__all__ = ["configure"]
