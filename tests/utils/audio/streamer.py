"""Audio streaming with real-time pacing for WebSocket client scripts."""

from __future__ import annotations

import json
import time
import base64
import asyncio
from typing import Any
from contextlib import suppress
from collections.abc import Callable

from tests import config

from .chunks import iter_pcm16_chunks


class AudioStreamer:
    """Stream PCM16 mono @16k audio as application frames with realtime pacing."""

    def __init__(
        self,
        pcm_bytes: bytes,
        *,
        debug: bool = False,
        sr: int = config.ASR_SAMPLE_RATE,
        chunk_samples: int = config.CHUNK_SAMPLES,
    ) -> None:
        self.pcm_bytes = pcm_bytes
        self.debug = debug
        self.sr = int(sr)
        self.chunk_samples = int(chunk_samples)
        self.chunk_bytes = self.chunk_samples * 2
        self.last_chunk_sent_ts = config.DEFAULT_ZERO

    async def stream_audio(
        self,
        ws,
        *,
        session_id: str,
        request_id: str,
        on_first_audio_sent: Callable[[float], None] | None = None,
    ) -> tuple[float, float]:
        """Stream audio in chunks paced to wall-clock time.

        Returns:
            (first_audio_sent_ts, last_signal_ts)
        """
        if self.debug:
            print("DEBUG: Starting audio stream")

        t_stream0 = time.perf_counter()
        first_chunk_sent_ts = config.DEFAULT_ZERO
        samples_sent = 0

        for chunk in iter_pcm16_chunks(self.pcm_bytes, chunk_bytes=self.chunk_bytes):
            if not chunk:
                continue

            audio_b64 = base64.b64encode(chunk).decode("ascii")
            msg: dict[str, Any] = {
                config.PROTO_KEY_TYPE: config.PROTO_TYPE_AUDIO_APPEND,
                config.PROTO_KEY_SESSION_ID: session_id,
                config.PROTO_KEY_REQUEST_ID: request_id,
                config.PROTO_KEY_PAYLOAD: {"audio": audio_b64},
            }
            await ws.send(json.dumps(msg))

            self.last_chunk_sent_ts = time.perf_counter()
            if first_chunk_sent_ts == config.DEFAULT_ZERO:
                first_chunk_sent_ts = self.last_chunk_sent_ts
                if on_first_audio_sent is not None:
                    with suppress(Exception):
                        on_first_audio_sent(first_chunk_sent_ts)

            samples_sent += len(chunk) // 2

            target = t_stream0 + (samples_sent / self.sr)
            sleep_for = target - time.perf_counter()
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                await asyncio.sleep(config.MIN_SLEEP_S)

        return (first_chunk_sent_ts or t_stream0), time.perf_counter()


__all__ = ["AudioStreamer"]
