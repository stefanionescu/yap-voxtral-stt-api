from __future__ import annotations

# Minimal sleep used when pacing or polling to avoid tight loops.
MIN_SLEEP_S: float = 0.001

# Poll interval for event waits (seconds).
POLL_INTERVAL_S: float = 0.01

# Handshake and completion wait windows (seconds).
READY_WAIT_TIMEOUT_S: float = 10.0
DONE_WAIT_TIMEOUT_S: float = 60.0

__all__ = ["DONE_WAIT_TIMEOUT_S", "MIN_SLEEP_S", "POLL_INTERVAL_S", "READY_WAIT_TIMEOUT_S"]
