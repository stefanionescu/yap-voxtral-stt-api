"""Common metric printing helpers shared across test output modules."""

from __future__ import annotations

from collections.abc import Callable

from tests.params import config

from .fmt import dim


def print_segment_metrics(
    seg: dict[str, float],
    *,
    audio_duration_s: float,
    to_final_s: float,
    sink: Callable[[str], None] = print,
) -> None:
    """Print common segment metrics (RTF, TTFW, timing details).

    Args:
        seg: Segment metrics dictionary
        audio_duration_s: Duration of audio in seconds
        to_final_s: Time to final result in seconds
        sink: Output function (default: print) for redirectable output
    """
    seg_rtf_full = seg.get("rtf_full")
    if seg_rtf_full is None and audio_duration_s > 0:
        seg_rtf_full = to_final_s / audio_duration_s if audio_duration_s > 0 else None
    if seg_rtf_full is not None:
        sink(f"RTF (full): {seg_rtf_full:.4f}")

    seg_rtf_server = seg.get("rtf_server") or seg.get("rtf_measured")
    if seg_rtf_server is not None:
        xrt = (1.0 / seg_rtf_server) if seg_rtf_server and seg_rtf_server > 0 else 0.0
        rtf_target = seg.get("rtf_target")
        sink(
            f"RTF (server): {seg_rtf_server:.4f}  xRT(server): {xrt:.2f}x  {dim(f'(target={rtf_target})')}",
        )
    ttfw_ms = (seg.get("ttfw_s", 0) * config.MS_PER_S) if seg.get("ttfw_s") is not None else 0.0
    sink(f"TTFW: {ttfw_ms:.1f}ms")
    sink(f"Delta (audio): {seg.get('delta_to_audio_ms', 0.0):.1f}ms")
    sink(f"Partials: {int(seg.get('partials', 0))}")
    sink(f"Flush→Final: {seg.get('finalize_ms', 0.0):.1f}ms")
    sink(f"Decode tail: {seg.get('decode_tail_ms', 0.0):.1f}ms")


__all__ = ["print_segment_metrics"]
