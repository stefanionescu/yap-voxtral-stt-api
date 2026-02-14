"""GPU-specific defaults.

This module intentionally contains only pure, dependency-light helpers so it can
be imported in unit tests without requiring CUDA / torch / vLLM.
"""

from __future__ import annotations


def select_max_num_batched_tokens(gpu_name: str | None) -> int:
    """Select vLLM max_num_batched_tokens based on GPU name.

    This is a throughput vs tail-latency knob. We keep it out of `.env` to avoid
    accidental footguns and instead choose sane defaults per GPU class.
    """

    name = (gpu_name or "").strip().upper()

    # Hopper / Blackwell: higher batch is usually safe and increases throughput.
    if "H100" in name or "B200" in name:
        return 4096

    # Ada: prefer smaller batches for realtime p95/p99 under concurrency.
    if "L40S" in name or "L40" in name:
        return 2048
    if "RTX 6000" in name or "RTX6000" in name:
        return 2048

    # Ampere: similar tail-latency behavior to Ada for this workload.
    if "A100" in name:
        return 2048

    # Placeholder until we confirm architecture/throughput characteristics.
    if "RTX 9000" in name or "RTX9000" in name:
        return 4096

    # Safe fallback.
    return 2048


__all__ = ["select_max_num_batched_tokens"]
