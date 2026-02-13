"""Client script utilities.

Focused modules:
- files.py: audio decoding and sample discovery
- network.py: ws url building and socket tweaks
- audio/: streaming and chunking helpers
- messages/: message handlers for streaming transcription
"""

from __future__ import annotations

from data.printing import (
    print_convo_metrics,
    print_file_not_found,
    print_transcript_line,
    print_benchmark_summary,
    print_single_stream_metrics,
)

from .audio import AudioStreamer, iter_pcm16_chunks
from .messages import MessageHandler, BenchMessageHandler
from .network import ws_url, is_cloud_host, append_auth_query, enable_tcp_nodelay
from .files import (
    EXTS,
    SAMPLES_DIR,
    find_sample_files,
    make_silence_pcm16,
    find_sample_by_name,
    file_duration_seconds,
    file_to_pcm16_mono_16k,
)

__all__ = [
    "EXTS",
    "SAMPLES_DIR",
    "AudioStreamer",
    "BenchMessageHandler",
    "MessageHandler",
    "append_auth_query",
    "enable_tcp_nodelay",
    "file_duration_seconds",
    "file_to_pcm16_mono_16k",
    "find_sample_by_name",
    "find_sample_files",
    "is_cloud_host",
    "iter_pcm16_chunks",
    "make_silence_pcm16",
    "print_benchmark_summary",
    "print_convo_metrics",
    "print_file_not_found",
    "print_single_stream_metrics",
    "print_transcript_line",
    "ws_url",
]
