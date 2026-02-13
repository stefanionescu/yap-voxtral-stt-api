#!/usr/bin/env python3
"""WebSocket remote client (warmup-equivalent for remote GPU)."""

from __future__ import annotations

import os
import asyncio
import logging
import argparse

from params import config
from client import RemoteClient
from data.printing import dim, format_error, section_header
from params.env import apply_key_overrides, derive_default_server
from utils import (
    SAMPLES_DIR,
    find_sample_files,
    find_sample_by_name,
    print_file_not_found,
    file_duration_seconds,
    print_transcript_line,
    file_to_pcm16_mono_16k,
    print_single_stream_metrics,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WebSocket remote client")
    default_server = derive_default_server()
    parser.add_argument("--server", default=default_server, help="host:port or ws://host:port or full URL")
    parser.add_argument("--secure", action="store_true", help="Use WSS")
    parser.add_argument("--file", type=str, default="mid.wav", help="Audio file from samples/")
    parser.add_argument("--debug", action="store_true", help="Print debug info including raw server messages")
    parser.add_argument("--full-text", action="store_true", help="Print full transcribed text (default: truncate)")
    parser.add_argument("--voxtral-key", type=str, default=None, help="API key (overrides VOXTRAL_API_KEY env)")
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    apply_key_overrides(args.voxtral_key)

    file_path = find_sample_by_name(args.file)
    if not file_path:
        available = find_sample_files()
        print_file_not_found(args.file, str(SAMPLES_DIR), available)
        return

    api_key = os.getenv(config.ENV_VOXTRAL_API_KEY)
    if not api_key:
        print(format_error("API key missing", f"use --voxtral-key or set {config.ENV_VOXTRAL_API_KEY}"))
        return

    pcm = file_to_pcm16_mono_16k(file_path)
    duration = file_duration_seconds(file_path)

    print(f"\n{section_header('REMOTE CLIENT')}")
    print(dim(f"  server: {args.server}"))
    print(dim(f"  file: {os.path.basename(file_path)}"))
    print()

    client = RemoteClient(args.server, args.secure, debug=args.debug)
    res = await client.run_stream(pcm, debug=args.debug)

    if res.get("error"):
        print(format_error("Stream error", str(res["error"])))

    print_transcript_line(res.get("text", ""), full=args.full_text, truncate=80)
    print_single_stream_metrics(client, res, duration)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING, format="%(levelname)s: %(message)s")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
