#!/usr/bin/env python3
"""Warmup via WebSocket streaming.

Quick health check for the STT server.
"""

from __future__ import annotations

import os
import asyncio
import logging
import argparse
from pathlib import Path

from tests import config
from tests.client import WarmupClient
from tests.data.printing import dim, format_error, section_header
from tests.utils.env import apply_key_overrides, derive_default_server
from tests.utils import (
    SAMPLES_DIR,
    find_sample_files,
    print_file_not_found,
    file_duration_seconds,
    print_transcript_line,
    file_to_pcm16_mono_16k,
    print_single_stream_metrics,
)

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Warmup via WebSocket streaming")
    default_server = derive_default_server()
    parser.add_argument("--server", type=str, default=default_server, help="host:port or ws://host:port or full URL")
    parser.add_argument("--secure", action="store_true")
    parser.add_argument("--file", type=str, default="mid.wav", help="Audio file. Absolute path or name in samples/")
    parser.add_argument("--debug", action="store_true", help="Print debug info including raw server messages")
    parser.add_argument("--full-text", action="store_true", help="Print full transcribed text (default: truncate)")
    parser.add_argument("--voxtral-key", type=str, default=None, help="API key (overrides VOXTRAL_API_KEY env)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING, format="%(levelname)s: %(message)s")

    candidate = Path(args.file)
    audio_path = candidate if candidate.is_absolute() and candidate.exists() else (SAMPLES_DIR / args.file)
    if not audio_path.exists():
        print_file_not_found(args.file, str(SAMPLES_DIR), find_sample_files())
        return 2

    apply_key_overrides(args.voxtral_key)

    api_key = os.getenv(config.ENV_VOXTRAL_API_KEY)
    if not api_key:
        print(format_error("API key missing", f"use --voxtral-key or set {config.ENV_VOXTRAL_API_KEY}"))
        return 1

    pcm_bytes = file_to_pcm16_mono_16k(str(audio_path))
    duration = file_duration_seconds(str(audio_path))

    print(f"\n{section_header('WARMUP')}")
    print(dim(f"  server: {args.server}"))
    print(dim(f"  file: {audio_path.name}"))
    print()

    client = WarmupClient(args.server, args.secure, debug=args.debug)
    res = asyncio.run(client.run_stream(pcm_bytes, debug=args.debug))

    if res.get("error"):
        print(format_error("Warmup error", str(res["error"])))
    print_transcript_line(res.get("text", ""), full=args.full_text, truncate=80)
    print_single_stream_metrics(client, res, duration)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
