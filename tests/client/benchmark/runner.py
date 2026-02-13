"""Standalone benchmark runner for the WebSocket client."""

from __future__ import annotations

import sys
import asyncio

from params import config

from .client import BenchClient, CapacityRejected
from .timeout import compute_stream_timeout_seconds_for


class BenchmarkRunner:
    def __init__(
        self,
        server: str,
        secure: bool = False,
        debug: bool = False,
    ):
        self.server = server
        self.secure = secure
        self.debug = debug

    async def run_benchmark(
        self,
        pcm_bytes: bytes,
        total_reqs: int,
        concurrency: int,
    ) -> tuple[list[dict[str, float]], int, int]:
        sem = asyncio.Semaphore(max(1, concurrency))
        results: list[dict[str, float]] = []
        rejected = 0
        errors_total = 0

        audio_seconds = len(pcm_bytes) // 2 / config.ASR_SAMPLE_RATE
        timeout = compute_stream_timeout_seconds_for(audio_seconds)

        async def worker(req_idx: int) -> None:
            nonlocal errors_total, rejected
            async with sem:
                if req_idx > 0:
                    await asyncio.sleep((req_idx % config.JITTER_GROUP_SIZE) * config.JITTER_STEP_S)
                try:
                    client = BenchClient(self.server, self.secure, self.debug)
                    result = await asyncio.wait_for(client.run_benchmark_session(pcm_bytes), timeout=timeout)
                    results.append(result)
                except CapacityRejected as exc:
                    rejected += 1
                    self._log_error(req_idx, f"REJECTED capacity: {exc}")
                except Exception as exc:
                    errors_total += 1
                    self._log_error(req_idx, f"err={exc}")

        tasks = [asyncio.create_task(worker(i)) for i in range(max(1, total_reqs))]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results[:total_reqs], rejected, errors_total

    def _log_error(self, req_idx: int, message: str) -> None:
        if not self.debug:
            return
        print(f"[bench] req={req_idx} | {message}", file=sys.stderr, flush=True)


__all__ = ["BenchmarkRunner"]
