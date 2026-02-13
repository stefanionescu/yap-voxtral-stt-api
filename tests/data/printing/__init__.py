"""Printing helpers split by concern (single stream, convo, summary)."""

from __future__ import annotations

from .convo import print_convo_metrics
from .misc import print_file_not_found
from .common import print_segment_metrics
from .summary import print_benchmark_summary
from .single import print_transcript_line, first_audio_relative_ms, print_single_stream_metrics
from .fmt import (
    dim,
    red,
    bold,
    cyan,
    green,
    yellow,
    magenta,
    format_fail,
    format_info,
    format_pass,
    test_header,
    emit_section,
    format_error,
    format_metric,
    format_warning,
    metrics_header,
    section_header,
    segment_header,
    format_metric_ms,
    format_count_line,
    format_metric_line,
    format_summary_header,
)

__all__ = [
    "bold",
    "cyan",
    "dim",
    "emit_section",
    "first_audio_relative_ms",
    "format_count_line",
    "format_error",
    "format_fail",
    "format_info",
    "format_metric",
    "format_metric_line",
    "format_metric_ms",
    "format_pass",
    "format_summary_header",
    "format_warning",
    "green",
    "magenta",
    "metrics_header",
    "print_benchmark_summary",
    "print_convo_metrics",
    "print_file_not_found",
    "print_segment_metrics",
    "print_single_stream_metrics",
    "print_transcript_line",
    "red",
    "section_header",
    "segment_header",
    "test_header",
    "yellow",
]
