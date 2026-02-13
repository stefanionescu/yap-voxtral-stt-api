#!/usr/bin/env python3
"""Warmup via WebSocket streaming (Voxtral Realtime)."""

from __future__ import annotations

import os
import sys
import uuid
import asyncio
import logging
import argparse
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.client import RealtimeClient  # noqa: E402
from tests.params.env import derive_default_server  # noqa: E402
from tests.data.printing import dim, format_error, section_header  # noqa: E402
from tests.data.printing.single import print_transcript_line, print_single_stream_metrics  # noqa: E402
from tests.utils import (  # noqa: E402
    SAMPLES_DIR,
    find_sample_files,
    make_silence_pcm16,
    find_sample_by_name,
    file_duration_seconds,
    file_to_pcm16_mono_16k,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Warmup via Voxtral /ws streaming")
    p.add_argument("--server", default=derive_default_server(), help="host:port or ws://host:port")
    p.add_argument("--secure", action="store_true", help="Use wss://")
    p.add_argument("--file", default="mid.wav", help="Audio file name in samples/ or absolute path")
    p.add_argument("--rtf", type=float, default=2.0, help="Real-time factor (1.0=realtime, >1 faster)")
    p.add_argument("--timeout", type=float, default=120.0, help="Timeout waiting for final (seconds)")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--full-text", action="store_true")
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    if not os.getenv("VOXTRAL_API_KEY"):
        print(format_error("VOXTRAL_API_KEY missing", "set VOXTRAL_API_KEY for test clients"))
        return 1

    pcm: bytes
    audio_duration_s: float
    file_path = args.file
    if os.path.isabs(file_path) and os.path.exists(file_path):
        pcm = file_to_pcm16_mono_16k(file_path)
        audio_duration_s = file_duration_seconds(file_path)
    else:
        sample = find_sample_by_name(file_path)
        if sample:
            pcm = file_to_pcm16_mono_16k(sample)
            audio_duration_s = file_duration_seconds(sample)
        else:
            # Fallback: silence still exercises the full protocol path.
            pcm = make_silence_pcm16(2.0)
            audio_duration_s = 2.0

    session_id = f"warmup-{uuid.uuid4()}"
    request_id = f"utt-{uuid.uuid4()}"

    print(f"\n{section_header('WARMUP')}")
    print(dim(f"  server: {args.server}"))
    print(dim(f"  samples dir: {SAMPLES_DIR}"))
    if not (os.path.isabs(args.file) and os.path.exists(args.file)) and not find_sample_by_name(args.file):
        avail = find_sample_files()
        if avail:
            print(dim(f"  note: samples missing '{args.file}', using silence (available: {len(avail)})"))
        else:
            print(dim("  note: samples directory empty, using silence"))
    else:
        print(dim(f"  file: {args.file}"))
    print()

    client = RealtimeClient(args.server, args.secure, debug=args.debug)
    res = await client.run_stream(
        pcm,
        session_id=session_id,
        request_id=request_id,
        rtf=args.rtf,
        timeout_s=float(args.timeout),
    )

    if res.error:
        print(format_error("Warmup error", str(res.error)))

    print_transcript_line(res.text, full=args.full_text, truncate=80)
    print_single_stream_metrics(client, res.metrics, audio_duration_s)

    return 0 if not res.error else 2


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING, format="%(levelname)s: %(message)s")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
