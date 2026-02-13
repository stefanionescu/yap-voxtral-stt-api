"""Remote single-stream client (separate from warmup for clarity)."""

from __future__ import annotations

import time
import uuid

from params import config
from utils.messages import MessageHandler
from client.shared.base import WSClientBase
from data.metrics import calculate_basic_metrics, calculate_detailed_metrics, compute_stream_timeout_seconds


class RemoteClient(WSClientBase):
    async def run_stream(self, pcm_bytes: bytes, *, debug: bool = False) -> dict:
        handler = MessageHandler(debug=debug)
        audio_duration_s = len(pcm_bytes) // 2 / config.ASR_SAMPLE_RATE

        session_id = f"remote-{uuid.uuid4()}"
        request_id = f"utt-{uuid.uuid4()}"
        timeout = compute_stream_timeout_seconds(audio_duration_s, wait_for_ready=True)

        session_start, last_signal_ts = await self._process_stream(
            pcm_bytes,
            handler,
            session_id=session_id,
            request_id=request_id,
            timeout_s=timeout,
        )

        wall = time.perf_counter() - session_start

        ttfw_text = None
        if handler.first_delta_ts is not None and self.first_audio_sent_ts:
            ttfw_text = float(handler.first_delta_ts - self.first_audio_sent_ts)

        basic = calculate_basic_metrics(audio_duration_s, wall, ttfw_text_s=ttfw_text)
        detailed = calculate_detailed_metrics(
            handler,
            last_chunk_sent_ts=self.last_chunk_sent_ts,
            t0=session_start,
            last_signal_ts=last_signal_ts,
            file_duration_s=audio_duration_s,
            first_audio_sent_ts=(self.first_audio_sent_ts or None),
        )

        return {
            "text": handler.final_text,
            "error": handler.error,
            "elapsed_s": wall,
            "ttfw_s": ttfw_text,
            "partials": float(len(handler.partial_ts)),
            "audio_s": float(audio_duration_s),
            **basic,
            **detailed,
        }


__all__ = ["RemoteClient"]
