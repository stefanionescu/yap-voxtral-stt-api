"""Metrics calculation and reporting utilities for client scripts."""

from __future__ import annotations

from params import config


def _compute_wall_to_final(handler, t0: float, last_signal_ts: float) -> float:
    if handler.final_recv_ts:
        return handler.final_recv_ts - t0
    return last_signal_ts - t0


def _compute_rtf_metrics(
    wall_to_final: float,
    fa_to_final: float | None,
    file_duration_s: float,
) -> tuple[float, float]:
    rtf_full = (wall_to_final / file_duration_s) if file_duration_s > 0 else 0.0
    rtf_server = fa_to_final / file_duration_s if fa_to_final is not None and file_duration_s > 0 else rtf_full
    return float(rtf_full), float(rtf_server)


def _compute_partial_gap_ms(handler) -> float:
    if len(handler.partial_ts) >= 2:
        gaps = [b - a for a, b in zip(handler.partial_ts[:-1], handler.partial_ts[1:], strict=False)]
        return float((sum(gaps) / len(gaps)) * config.MS_PER_S)
    return 0.0


def _compute_latency_metrics(handler, last_signal_ts: float) -> dict[str, float]:
    finalize_ms = max(
        0.0,
        float(((handler.final_recv_ts - last_signal_ts) * config.MS_PER_S) if handler.final_recv_ts else 0.0),
    )
    decode_tail_ms = float(
        (((handler.final_recv_ts - handler.last_partial_ts) * config.MS_PER_S) if handler.final_recv_ts else 0.0),
    )
    return {"finalize_ms": finalize_ms, "decode_tail_ms": decode_tail_ms}


def _compute_processing_metrics(
    last_chunk_sent_ts: float,
    t0: float,
    handler,
    last_signal_ts: float,
    file_duration_s: float,
    wall_to_final: float,
) -> dict[str, float]:
    return {
        "send_duration_s": float((last_chunk_sent_ts - t0) if last_chunk_sent_ts else 0.0),
        "post_send_final_s": float(
            ((handler.final_recv_ts - last_chunk_sent_ts) if (handler.final_recv_ts and last_chunk_sent_ts) else 0.0),
        ),
        "delta_to_audio_ms": float((wall_to_final - file_duration_s) * config.MS_PER_S),
        "flush_to_final_ms": float(
            (((handler.final_recv_ts - last_signal_ts) * config.MS_PER_S) if handler.final_recv_ts else 0.0),
        ),
    }


def calculate_basic_metrics(
    audio_duration_s: float,
    wall_s: float,
    ttfw_text_s: float | None = None,
) -> dict[str, float]:
    rtf = wall_s / audio_duration_s if audio_duration_s > 0 else float("inf")
    xrt = (audio_duration_s / wall_s) if wall_s > 0 else 0.0
    throughput_min_per_min = (audio_duration_s / wall_s) if wall_s > 0 else 0.0

    metrics = {
        "wall_s": float(wall_s),
        "audio_s": float(audio_duration_s),
        "rtf": float(rtf),
        "rtf_full": float(rtf),
        "xrt": float(xrt),
        "throughput_min_per_min": float(throughput_min_per_min),
    }
    if ttfw_text_s is not None:
        metrics["ttfw_text_s"] = float(ttfw_text_s)
    return metrics


def calculate_detailed_metrics(
    handler,
    *,
    last_chunk_sent_ts: float,
    t0: float,
    last_signal_ts: float,
    file_duration_s: float,
    first_audio_sent_ts: float | None = None,
) -> dict[str, float]:
    wall_to_final = _compute_wall_to_final(handler, t0, last_signal_ts)

    if first_audio_sent_ts:
        fa_to_final = (
            (handler.final_recv_ts - first_audio_sent_ts)
            if handler.final_recv_ts
            else (last_signal_ts - first_audio_sent_ts)
        )
    else:
        fa_to_final = None

    rtf_full, rtf_server = _compute_rtf_metrics(wall_to_final, fa_to_final, file_duration_s)

    metrics: dict[str, float] = {
        "wall_to_final_s": float(wall_to_final),
        "rtf_full": float(rtf_full),
        "rtf_server": float(rtf_server),
        "rtf_measured": float(rtf_server),
        "partials": float(len(handler.partial_ts)),
        "final_len_chars": float(len(handler.final_text)),
        "rtf_target": 1.0,
    }
    if fa_to_final is not None:
        metrics["first_audio_to_final_s"] = float(fa_to_final)

    metrics["avg_partial_gap_ms"] = _compute_partial_gap_ms(handler)
    metrics.update(_compute_latency_metrics(handler, last_signal_ts))
    metrics.update(
        _compute_processing_metrics(
            last_chunk_sent_ts,
            t0,
            handler,
            last_signal_ts,
            file_duration_s,
            wall_to_final,
        ),
    )
    return metrics


def compute_stream_timeout_seconds(audio_seconds: float, *, wait_for_ready: bool) -> float:
    """Compute a realistic session timeout using realtime pacing and finalize windows."""
    stream_time = float(audio_seconds)
    finalize_allowance = config.FINALIZE_ALLOWANCE_EXTRA_S
    handshake_allowance = config.HANDSHAKE_ALLOWANCE_WAIT_S if wait_for_ready else config.HANDSHAKE_ALLOWANCE_NO_WAIT_S
    base = stream_time + finalize_allowance + handshake_allowance
    timeout = max(
        config.COMPUTE_TIMEOUT_MIN_S,
        base * config.COMPUTE_TIMEOUT_SAFETY_MULT + config.COMPUTE_TIMEOUT_SAFETY_ADD_S,
    )
    return min(timeout, config.COMPUTE_TIMEOUT_MAX_S)


__all__ = [
    "calculate_basic_metrics",
    "calculate_detailed_metrics",
    "compute_stream_timeout_seconds",
]
