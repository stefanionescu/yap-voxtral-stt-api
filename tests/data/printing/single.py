"""Single stream metrics printing with consistent formatting."""

from __future__ import annotations

from collections.abc import Callable

from tests.params.config import MS_PER_S

from .fmt import metrics_header
from .common import print_segment_metrics

# ============================================================================
# Internal Helpers
# ============================================================================


def _print_single_common(
    client,
    *,
    header: bool = True,
    sink: Callable[[str], None] = print,
) -> None:
    """Print common metrics shared across single-stream tests."""
    if header:
        sink(metrics_header())
    sink(
        f"Connect: {client.connect_elapsed_s * MS_PER_S:.1f}ms  "
        f"Handshake(Ready): {client.handshake_elapsed_s * MS_PER_S:.1f}ms  "
        f"FirstAudio: {first_audio_relative_ms(client):.1f}ms",
    )


# ============================================================================
# Public API
# ============================================================================


def first_audio_relative_ms(client) -> float:
    """Calculate time from session start to first audio sent."""
    if getattr(client, "first_audio_sent_ts", 0.0) and getattr(client, "session_start_ts", 0.0):
        return (client.first_audio_sent_ts - client.session_start_ts) * MS_PER_S
    return 0.0


def print_transcript_line(
    text: str,
    *,
    full: bool,
    truncate: int,
    sink: Callable[[str], None] = print,
) -> None:
    """Print transcript text, optionally truncated."""
    if full:
        sink(text or "")
    else:
        t = text or ""
        sink(t[:truncate] + "..." if len(t) > truncate else t)


def print_single_stream_metrics(
    client,
    result: dict[str, float],
    audio_duration_s: float,
    sink: Callable[[str], None] = print,
) -> None:
    """Print comprehensive metrics for a single stream test.

    Args:
        client: WebSocket client with timing attributes
        result: Dictionary of result metrics
        audio_duration_s: Duration of audio in seconds
        sink: Output function (default: print) for redirectable output
    """
    _print_single_common(client, header=True, sink=sink)
    sink(f"Audio duration: {audio_duration_s:.4f}s")
    to_final_s = result.get("wall_to_final_s", 0.0)
    sink(f"Transcription time (to Final): {to_final_s:.4f}s")
    final_minus_connect_ms = max(0.0, (to_final_s - client.connect_elapsed_s) * MS_PER_S)
    final_minus_first_audio_ms = 0.0
    if getattr(client, "first_audio_sent_ts", 0.0) and getattr(client, "session_start_ts", 0.0):
        first_audio_offset_s = client.first_audio_sent_ts - client.session_start_ts
        final_minus_first_audio_ms = max(0.0, (to_final_s - first_audio_offset_s) * MS_PER_S)
    sink(
        f"Final-Connect: {final_minus_connect_ms:.1f}ms  Final-FirstAudio: {final_minus_first_audio_ms:.1f}ms",
    )
    print_segment_metrics(
        result,
        audio_duration_s=audio_duration_s,
        to_final_s=to_final_s,
        sink=sink,
    )
    sink(
        f"Close: {client.close_elapsed_s * MS_PER_S:.1f}ms  "
        f"Post-final (finish): {client.finish_elapsed_s * MS_PER_S:.1f}ms  "
        f"Session: {client.session_elapsed_s * MS_PER_S:.1f}ms",
    )


__all__ = ["first_audio_relative_ms", "print_single_stream_metrics", "print_transcript_line"]
