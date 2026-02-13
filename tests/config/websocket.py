"""WebSocket defaults for client scripts."""

from __future__ import annotations

from src.config.websocket import WS_ENDPOINT_PATH as _SERVER_WS_ENDPOINT_PATH

# Endpoint (server path). Clients build ws(s)://host:port + this path.
WS_ENDPOINT_PATH: str = _SERVER_WS_ENDPOINT_PATH

# Disable protocol-level ping/pong by default; the server's idle policy is based
# on receiving application messages (including {"type":"ping"}).
WS_PING_INTERVAL_S: float | None = None
WS_PING_TIMEOUT_S: float | None = None

# Close codes (used by client helpers)
WS_CLOSE_CODE_NORMAL: int = 1000

# Maximum WebSocket message size (bytes)
WS_MAX_MESSAGE_BYTES: int = 32 * 1024 * 1024

# For display/debug output only.
WS_CLOSE_REASON_CLIENT_DONE: str = "client_done"
