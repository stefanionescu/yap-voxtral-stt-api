from __future__ import annotations

from data.metrics import calculate_detailed_metrics


def calculate_segment_metrics(
    handler,
    results: dict[str, float],
    segment_start: float,
    duration_s: float,
) -> dict:
    return calculate_detailed_metrics(
        handler,
        last_chunk_sent_ts=results["last_chunk_sent_ts"],
        t0=segment_start,
        last_signal_ts=results["last_signal_ts"],
        file_duration_s=duration_s,
        first_audio_sent_ts=results.get("first_audio_sent_ts") or None,
    )


def build_conversation_result(
    seg1_handler,
    seg2_handler,
    seg1_metrics: dict,
    seg2_metrics: dict,
    dur1_s: float,
    dur2_s: float,
    *,
    seg1_ttfw_s: float | None,
    seg2_ttfw_s: float | None,
) -> dict:
    return {
        "text": f"{seg1_handler.final_text} {seg2_handler.final_text}".strip(),
        "seg1": {
            "text": seg1_handler.final_text,
            "ttfw_s": seg1_ttfw_s,
            "audio_s": dur1_s,
            **seg1_metrics,
        },
        "seg2": {
            "text": seg2_handler.final_text,
            "ttfw_s": seg2_ttfw_s,
            "audio_s": dur2_s,
            **seg2_metrics,
        },
    }


__all__ = ["build_conversation_result", "calculate_segment_metrics"]
