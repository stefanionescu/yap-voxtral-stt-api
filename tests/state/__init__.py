"""Test client state types (dataclasses only)."""

from __future__ import annotations

from .idle import IdleTestResult
from .convo import HandlerSnapshot

__all__ = [
    "HandlerSnapshot",
    "IdleTestResult",
]
