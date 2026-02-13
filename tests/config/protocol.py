from __future__ import annotations

# Envelope keys
PROTO_KEY_TYPE: str = "type"
PROTO_KEY_SESSION_ID: str = "session_id"
PROTO_KEY_REQUEST_ID: str = "request_id"
PROTO_KEY_PAYLOAD: str = "payload"

# Client message types
PROTO_TYPE_PING: str = "ping"
PROTO_TYPE_PONG: str = "pong"
PROTO_TYPE_END: str = "end"
PROTO_TYPE_CANCEL: str = "cancel"

PROTO_TYPE_SESSION_UPDATE: str = "session.update"
PROTO_TYPE_AUDIO_APPEND: str = "input_audio_buffer.append"
PROTO_TYPE_AUDIO_COMMIT: str = "input_audio_buffer.commit"

# Server message types
PROTO_TYPE_ERROR: str = "error"
PROTO_TYPE_TRANSCRIPTION_DELTA: str = "transcription.delta"
PROTO_TYPE_TRANSCRIPTION_DONE: str = "transcription.done"
PROTO_TYPE_SESSION_CREATED: str = "session.created"
PROTO_TYPE_SESSION_UPDATED: str = "session.updated"

__all__ = [
    "PROTO_KEY_PAYLOAD",
    "PROTO_KEY_REQUEST_ID",
    "PROTO_KEY_SESSION_ID",
    "PROTO_KEY_TYPE",
    "PROTO_TYPE_AUDIO_APPEND",
    "PROTO_TYPE_AUDIO_COMMIT",
    "PROTO_TYPE_CANCEL",
    "PROTO_TYPE_END",
    "PROTO_TYPE_ERROR",
    "PROTO_TYPE_PING",
    "PROTO_TYPE_PONG",
    "PROTO_TYPE_SESSION_CREATED",
    "PROTO_TYPE_SESSION_UPDATE",
    "PROTO_TYPE_SESSION_UPDATED",
    "PROTO_TYPE_TRANSCRIPTION_DELTA",
    "PROTO_TYPE_TRANSCRIPTION_DONE",
]
