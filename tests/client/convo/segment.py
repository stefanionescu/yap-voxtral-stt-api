from __future__ import annotations

import json
import time

import config
from utils.audio import AudioStreamer


async def process_conversation_segment(
    base,
    ws,
    pcm_bytes: bytes,
    *,
    session_id: str,
    request_id: str,
    handler,
    debug: bool,
) -> dict[str, float]:
    """Run a single conversation segment on an existing connection."""
    await ws.send(
        json.dumps({
            config.PROTO_KEY_TYPE: config.PROTO_TYPE_AUDIO_COMMIT,
            config.PROTO_KEY_SESSION_ID: session_id,
            config.PROTO_KEY_REQUEST_ID: request_id,
            config.PROTO_KEY_PAYLOAD: {"final": False},
        })
    )

    first_audio_sent_ts = config.DEFAULT_ZERO

    def on_first_audio_sent(ts: float) -> None:
        nonlocal first_audio_sent_ts
        first_audio_sent_ts = ts
        if getattr(base, "first_audio_sent_ts", 0.0) == config.DEFAULT_ZERO:
            base.first_audio_sent_ts = ts

    streamer = AudioStreamer(pcm_bytes, debug=debug)
    await streamer.stream_audio(
        ws, session_id=session_id, request_id=request_id, on_first_audio_sent=on_first_audio_sent
    )
    base.last_chunk_sent_ts = streamer.last_chunk_sent_ts

    await ws.send(
        json.dumps({
            config.PROTO_KEY_TYPE: config.PROTO_TYPE_AUDIO_COMMIT,
            config.PROTO_KEY_SESSION_ID: session_id,
            config.PROTO_KEY_REQUEST_ID: request_id,
            config.PROTO_KEY_PAYLOAD: {"final": True},
        })
    )
    last_signal_ts = time.perf_counter()

    return {
        "first_audio_sent_ts": float(first_audio_sent_ts),
        "last_chunk_sent_ts": float(streamer.last_chunk_sent_ts or 0.0),
        "last_signal_ts": float(last_signal_ts),
    }


__all__ = ["process_conversation_segment"]
