"""Conversation metrics printing with consistent formatting."""

from __future__ import annotations

from collections.abc import Callable

from params import config

from .fmt import segment_header
from .common import print_segment_metrics
from .single import first_audio_relative_ms


def print_convo_metrics(
    client,
    res: dict[str, dict[str, float]],
    sink: Callable[[str], None] = print,
) -> None:
    # Segment 1
    seg1 = res.get("seg1", {})
    sink(segment_header(1))
    sink(
        f"Connect: {client.connect_elapsed_s * config.MS_PER_S:.1f}ms  "
        f"Handshake(Ready): {client.handshake_elapsed_s * config.MS_PER_S:.1f}ms  "
        f"FirstAudio: {first_audio_relative_ms(client):.1f}ms",
    )
    sink(f"Audio duration: {seg1.get('audio_s', 0.0):.4f}s")
    to_final_s1 = seg1.get("wall_to_final_s", 0.0)
    sink(f"Transcription time (to Final): {to_final_s1:.4f}s")
    final_minus_connect_ms1 = max(0.0, (to_final_s1 - client.connect_elapsed_s) * config.MS_PER_S)
    final_minus_first_audio_ms1 = 0.0
    if getattr(client, "first_audio_sent_ts", 0.0) and getattr(client, "session_start_ts", 0.0):
        first_audio_offset_s = client.first_audio_sent_ts - client.session_start_ts
        final_minus_first_audio_ms1 = max(0.0, (to_final_s1 - first_audio_offset_s) * config.MS_PER_S)
    sink(
        f"Final-Connect: {final_minus_connect_ms1:.1f}ms  Final-FirstAudio: {final_minus_first_audio_ms1:.1f}ms",
    )
    print_segment_metrics(seg1, audio_duration_s=seg1.get("audio_s", 0.0), to_final_s=to_final_s1, sink=sink)

    # Segment 2
    seg2 = res.get("seg2", {})
    sink(segment_header(2))
    sink(f"Audio duration: {seg2.get('audio_s', 0.0):.4f}s")
    to_final_s2 = seg2.get("wall_to_final_s", 0.0)
    sink(f"Transcription time (to Final): {to_final_s2:.4f}s")
    sink(f"Final-Segment2Start: {to_final_s2 * config.MS_PER_S:.1f}ms")
    if seg2.get("first_audio_to_final_s") is not None:
        final_minus_first_audio_ms2 = seg2["first_audio_to_final_s"] * config.MS_PER_S
        sink(f"Final-FirstAudio: {final_minus_first_audio_ms2:.1f}ms")
    print_segment_metrics(seg2, audio_duration_s=seg2.get("audio_s", 0.0), to_final_s=to_final_s2, sink=sink)

    sink(
        f"\nClose: {client.close_elapsed_s * config.MS_PER_S:.1f}ms  "
        f"Post-final (finish): {client.finish_elapsed_s * config.MS_PER_S:.1f}ms  "
        f"Session: {client.session_elapsed_s * config.MS_PER_S:.1f}ms",
    )


__all__ = ["print_convo_metrics"]
