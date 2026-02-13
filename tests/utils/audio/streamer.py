from __future__ import annotations

import json
import time
import base64
import asyncio
from typing import Any
from collections.abc import Callable

from tests.params import config

from .chunks import iter_pcm16_chunks


class AudioStreamer:
    def __init__(
        self,
        *,
        rtf: float,
        sr: int = config.ASR_SAMPLE_RATE,
        chunk_samples: int = config.CHUNK_SAMPLES,
    ) -> None:
        self.rtf = max(0.01, float(rtf))
        self.sr = int(sr)
        self.chunk_samples = int(chunk_samples)
        self.chunk_bytes = self.chunk_samples * 2

    async def stream(
        self,
        ws,
        *,
        session_id: str,
        request_id: str,
        pcm_bytes: bytes,
        on_first_audio: Callable[[float], None] | None = None,
    ) -> dict[str, float]:
        t0 = time.perf_counter()
        t_stream0 = time.perf_counter()
        first_sent_ts: float | None = None

        samples_sent = 0
        for chunk in iter_pcm16_chunks(pcm_bytes, chunk_bytes=self.chunk_bytes):
            if not chunk:
                continue
            if first_sent_ts is None:
                first_sent_ts = time.perf_counter()
                if on_first_audio is not None:
                    on_first_audio(first_sent_ts)

            audio_b64 = base64.b64encode(chunk).decode("ascii")
            msg: dict[str, Any] = {
                "type": "input_audio_buffer.append",
                "session_id": session_id,
                "request_id": request_id,
                "payload": {"audio": audio_b64},
            }
            await ws.send(json.dumps(msg))

            samples_sent += len(chunk) // 2
            target = t_stream0 + (samples_sent / self.sr) / self.rtf
            now = time.perf_counter()
            if now < target:
                await asyncio.sleep(target - now)

        send_end = time.perf_counter()
        return {
            "send_duration_s": send_end - t0,
            "send_finish_ts": send_end,
            "first_audio_sent_ts": first_sent_ts or 0.0,
        }


__all__ = ["AudioStreamer"]
