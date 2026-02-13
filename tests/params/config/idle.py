"""Idle behavior configuration for client scripts."""

from __future__ import annotations

# Server idle timeout default (matches server default unless overridden).
SERVER_IDLE_TIMEOUT_S: float = 150.0

# Grace period added to idle timeout for client tolerance.
IDLE_GRACE_PERIOD_S: float = 5.0

__all__ = ["IDLE_GRACE_PERIOD_S", "SERVER_IDLE_TIMEOUT_S"]
