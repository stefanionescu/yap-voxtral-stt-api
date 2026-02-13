from __future__ import annotations

# Disable websockets library keepalive; we use explicit {"type":"ping"} frames.
WS_PING_INTERVAL_S: float | None = None
WS_PING_TIMEOUT_S: float | None = None
