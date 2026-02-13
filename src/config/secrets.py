"""Secrets and authentication configuration."""

from __future__ import annotations

import os


def get_voxtral_api_key() -> str:
    return (os.getenv("VOXTRAL_API_KEY") or "").strip()


__all__ = ["get_voxtral_api_key"]
