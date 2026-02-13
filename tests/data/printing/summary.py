"""Benchmark summary printing with consistent formatting."""

from __future__ import annotations

import statistics as stats
from collections.abc import Callable

from .fmt import dim, bold, format_metric_ms, format_metric_line, format_summary_header

# ============================================================================
# Internal Helpers
# ============================================================================


def _percentile(values: list[float], q: float) -> float:
    """Return the q-quantile using the existing discrete method."""
    if not values:
        return 0.0
    k = max(0, min(len(values) - 1, round(q * (len(values) - 1))))
    return sorted(values)[k]


def _print_core_metrics(
    *,
    title: str,
    sink: Callable[[str], None],
    n: int,
    wall: list[float],
    audio: list[float],
    ttfw_word_vals: list[float],
    ttfw_text_vals: list[float],
    rtf_full_vals: list[float],
    rtf_server_vals: list[float],
    xrt: list[float],
    throughput: list[float],
) -> None:
    sink(format_summary_header(title))
    sink(f"{bold('n')}={n}")
    sink(
        format_metric_line(
            "Wall s",
            avg=stats.mean(wall),
            p50=stats.median(wall),
            p95=_percentile(wall, 0.95),
        )
    )
    if ttfw_word_vals:
        sink(
            format_metric_line(
                "TTFW(word)",
                avg=stats.mean(ttfw_word_vals),
                p50=stats.median(ttfw_word_vals),
                p95=_percentile(ttfw_word_vals, 0.95),
            )
        )
    if ttfw_text_vals:
        sink(
            format_metric_line(
                "TTFW(text)",
                avg=stats.mean(ttfw_text_vals),
                p50=stats.median(ttfw_text_vals),
                p95=_percentile(ttfw_text_vals, 0.95),
            )
        )
    sink(f"{'Audio s':<14} | avg={stats.mean(audio):.4f}")
    if rtf_full_vals:
        sink(
            format_metric_line(
                "RTF (full)",
                avg=stats.mean(rtf_full_vals),
                p50=stats.median(rtf_full_vals),
                p95=_percentile(rtf_full_vals, 0.95),
            )
        )
    if rtf_server_vals:
        sink(
            format_metric_line(
                "RTF (server)",
                avg=stats.mean(rtf_server_vals),
                p50=stats.median(rtf_server_vals),
                p95=_percentile(rtf_server_vals, 0.95),
            )
        )
    sink(f"{'xRT':<14} | avg={stats.mean(xrt):.4f}")
    sink(f"{'Throughput':<14} | avg={stats.mean(throughput):.2f} min/min")


def _print_latency_metrics(
    *,
    sink: Callable[[str], None],
    deltas: list[float],
    sendd: list[float],
    postf: list[float],
    f2f: list[float],
    dtail: list[float],
    gaps: list[float],
) -> None:
    if deltas:
        sink(
            format_metric_ms(
                "Delta(audio)",
                avg=stats.mean(deltas),
                p50=_percentile(deltas, 0.50),
                p95=_percentile(deltas, 0.95),
            )
        )
    if sendd:
        sink(
            format_metric_line(
                "Send dur s",
                avg=stats.mean(sendd),
                p50=stats.median(sendd),
                p95=_percentile(sendd, 0.95),
            )
        )
    if postf:
        sink(
            format_metric_line(
                "Post-send→Final",
                avg=stats.mean(postf),
                p50=stats.median(postf),
                p95=_percentile(postf, 0.95),
                unit="s",
            )
        )
    if f2f:
        sink(
            format_metric_ms(
                "Flush→Final",
                avg=stats.mean(f2f),
                p50=_percentile(f2f, 0.50),
                p95=_percentile(f2f, 0.95),
            )
        )
    if dtail:
        sink(
            format_metric_ms(
                "Decode tail",
                avg=stats.mean(dtail),
                p50=_percentile(dtail, 0.50),
                p95=_percentile(dtail, 0.95),
            )
        )
    if gaps:
        sink(
            format_metric_ms(
                "Partial gap",
                avg=stats.mean(gaps),
                p50=_percentile(gaps, 0.50),
                p95=_percentile(gaps, 0.95),
            )
        )


# ============================================================================
# Public API
# ============================================================================


def print_benchmark_summary(
    title: str,
    results: list[dict[str, float]],
    sink: Callable[[str], None] = print,
) -> None:
    """Print benchmark summary with formatted metrics.

    Args:
        title: Summary section title
        results: List of benchmark result dictionaries
        sink: Output function (default: print) for redirectable output
    """
    if not results:
        sink(f"{title}: {dim('no results')}")
        return

    wall = [r["wall_s"] for r in results]
    audio = [r["audio_s"] for r in results]
    rtf_full_vals: list[float] = []
    for r in results:
        v = r.get("rtf_full")
        if v is None:
            v = r.get("rtf")
        if v is not None:
            rtf_full_vals.append(v)

    rtf_server_vals: list[float] = []
    for r in results:
        v = r.get("rtf_server")
        if v is None:
            v = r.get("rtf_measured")
        if v is not None:
            rtf_server_vals.append(v)
    xrt = [r["xrt"] for r in results]
    throughput = [r["throughput_min_per_min"] for r in results]
    ttfw_word_vals = [r["ttfw_word_s"] for r in results if "ttfw_word_s" in r]
    ttfw_text_vals = [r["ttfw_text_s"] for r in results if "ttfw_text_s" in r]
    gaps = [r.get("avg_partial_gap_ms", 0.0) for r in results if r.get("avg_partial_gap_ms", 0.0) > 0]

    deltas = [r["delta_to_audio_ms"] for r in results if "delta_to_audio_ms" in r]
    sendd = [r["send_duration_s"] for r in results if "send_duration_s" in r]
    postf = [r["post_send_final_s"] for r in results if "post_send_final_s" in r]
    f2f = [r["flush_to_final_ms"] for r in results if "flush_to_final_ms" in r and r["flush_to_final_ms"] > 0]
    dtail = [r["decode_tail_ms"] for r in results if "decode_tail_ms" in r]
    _print_core_metrics(
        title=title,
        sink=sink,
        n=len(results),
        wall=wall,
        audio=audio,
        ttfw_word_vals=ttfw_word_vals,
        ttfw_text_vals=ttfw_text_vals,
        rtf_full_vals=rtf_full_vals,
        rtf_server_vals=rtf_server_vals,
        xrt=xrt,
        throughput=throughput,
    )
    _print_latency_metrics(
        sink=sink,
        deltas=deltas,
        sendd=sendd,
        postf=postf,
        f2f=f2f,
        dtail=dtail,
        gaps=gaps,
    )


__all__ = ["print_benchmark_summary"]
