"""WebSocket protocol configuration and constants."""

from __future__ import annotations

import os

# Envelope keys (Yap-style)
WS_KEY_TYPE = "type"
WS_KEY_SESSION_ID = "session_id"
WS_KEY_REQUEST_ID = "request_id"
WS_KEY_PAYLOAD = "payload"

# Close codes
WS_CLOSE_CLIENT_REQUEST_CODE = 1000
WS_CLOSE_UNAUTHORIZED_CODE = 4001
WS_CLOSE_BUSY_CODE = 4002
WS_CLOSE_IDLE_CODE = 4000

WS_CLOSE_IDLE_REASON = "idle timeout"

# Idle watchdog
WS_IDLE_TIMEOUT_S = float(os.getenv("WS_IDLE_TIMEOUT_S", "150"))
WS_WATCHDOG_TICK_S = float(os.getenv("WS_WATCHDOG_TICK_S", "5"))

# Errors (payload.code values)
WS_ERROR_AUTH_FAILED = "authentication_failed"
WS_ERROR_SERVER_AT_CAPACITY = "server_at_capacity"
WS_ERROR_INVALID_MESSAGE = "invalid_message"
WS_ERROR_INVALID_PAYLOAD = "invalid_payload"
WS_ERROR_RATE_LIMITED = "rate_limited"
WS_ERROR_INTERNAL = "internal_error"

__all__ = [
    "WS_KEY_TYPE",
    "WS_KEY_SESSION_ID",
    "WS_KEY_REQUEST_ID",
    "WS_KEY_PAYLOAD",
    "WS_CLOSE_CLIENT_REQUEST_CODE",
    "WS_CLOSE_UNAUTHORIZED_CODE",
    "WS_CLOSE_BUSY_CODE",
    "WS_CLOSE_IDLE_CODE",
    "WS_CLOSE_IDLE_REASON",
    "WS_IDLE_TIMEOUT_S",
    "WS_WATCHDOG_TICK_S",
    "WS_ERROR_AUTH_FAILED",
    "WS_ERROR_SERVER_AT_CAPACITY",
    "WS_ERROR_INVALID_MESSAGE",
    "WS_ERROR_INVALID_PAYLOAD",
    "WS_ERROR_RATE_LIMITED",
    "WS_ERROR_INTERNAL",
]
