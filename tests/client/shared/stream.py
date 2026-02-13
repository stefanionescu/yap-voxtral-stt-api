"""Audio streaming helpers for WebSocket client sessions."""

from __future__ import annotations

from tests.utils.audio import AudioStreamer


def create_streamer(pcm_bytes: bytes, debug: bool) -> AudioStreamer:
    return AudioStreamer(pcm_bytes, debug=debug)


async def stream_audio_with_callback(
    ws, streamer: AudioStreamer, handler, base, *, session_id: str, request_id: str
) -> float:
    def on_first_audio_sent(timestamp: float) -> None:
        base.first_audio_sent_ts = timestamp

    _, last_signal_ts = await streamer.stream_audio(
        ws,
        session_id=session_id,
        request_id=request_id,
        on_first_audio_sent=on_first_audio_sent,
    )
    base.last_chunk_sent_ts = streamer.last_chunk_sent_ts
    return last_signal_ts


__all__ = ["create_streamer", "stream_audio_with_callback"]
