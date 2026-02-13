"""Benchmark client for single-stream sessions with capacity handling."""

from __future__ import annotations

import time
import uuid

import config
from client.shared.base import WSClientBase
from utils.messages import BenchMessageHandler
from data.metrics import calculate_basic_metrics, calculate_detailed_metrics

from .timeout import compute_stream_timeout_seconds_for


class CapacityRejected(Exception):  # noqa: N818
    """Raised when server rejects due to capacity."""


class BenchClient(WSClientBase):
    async def run_benchmark_session(self, pcm_bytes: bytes) -> dict[str, float]:
        handler = BenchMessageHandler(debug=self.debug)
        audio_duration_s = len(pcm_bytes) // 2 / config.ASR_SAMPLE_RATE

        session_id = f"bench-{uuid.uuid4()}"
        request_id = f"utt-{uuid.uuid4()}"
        timeout = compute_stream_timeout_seconds_for(audio_duration_s)

        session_start, last_signal_ts = await self._process_stream(
            pcm_bytes,
            handler,
            session_id=session_id,
            request_id=request_id,
            timeout_s=timeout,
        )

        if handler.reject_reason == "capacity":
            raise CapacityRejected("server_at_capacity")

        wall = time.perf_counter() - session_start

        ttfw_text = None
        if handler.first_delta_ts is not None and self.first_audio_sent_ts:
            ttfw_text = float(handler.first_delta_ts - self.first_audio_sent_ts)

        basic_metrics = calculate_basic_metrics(audio_duration_s, wall, ttfw_text_s=ttfw_text)
        detailed_metrics = calculate_detailed_metrics(
            handler,
            last_chunk_sent_ts=self.last_chunk_sent_ts,
            t0=session_start,
            last_signal_ts=last_signal_ts,
            file_duration_s=audio_duration_s,
            first_audio_sent_ts=(self.first_audio_sent_ts or None),
        )

        return {**basic_metrics, **detailed_metrics}


__all__ = ["BenchClient", "CapacityRejected"]
