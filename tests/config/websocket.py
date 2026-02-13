from __future__ import annotations

"""WebSocket defaults for client scripts."""

# Endpoint (server path). Clients build ws(s)://host:port + this path.
WS_ENDPOINT_PATH: str = "/api/asr-streaming"

# Disable protocol-level ping/pong by default; the server's idle policy is based
# on receiving application messages (including {"type":"ping"}).
WS_PING_INTERVAL_S: float | None = None
WS_PING_TIMEOUT_S: float | None = None

# Close codes (used by client helpers)
WS_CLOSE_CODE_NORMAL: int = 1000

# Maximum WebSocket message size (bytes)
WS_MAX_MESSAGE_BYTES: int = 32 * 1024 * 1024

# Application-level ping interval to keep connections alive while waiting for
# long-running transcripts.
WS_APP_PING_INTERVAL_S: float = 30.0

# For display/debug output only.
WS_CLOSE_REASON_CLIENT_DONE: str = "client_done"
