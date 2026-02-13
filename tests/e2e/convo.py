#!/usr/bin/env python3
"""Two-file conversation test over a single WebSocket connection."""

from __future__ import annotations

import os
import asyncio
import argparse

from tests.client import ConvoClient
from tests.data.printing import dim, section_header
from tests.utils.env import apply_key_overrides, derive_default_server
from tests.utils import (
    SAMPLES_DIR,
    find_sample_files,
    find_sample_by_name,
    print_convo_metrics,
    print_file_not_found,
    file_duration_seconds,
    print_transcript_line,
    file_to_pcm16_mono_16k,
)


def parse_args() -> argparse.Namespace:
    default_server = derive_default_server()

    p = argparse.ArgumentParser(description="Two-file WebSocket conversation test")
    p.add_argument("--server", default=default_server, help="host:port or ws://host:port or full URL")
    p.add_argument("--secure", action="store_true", help="Use WSS")
    p.add_argument("--file1", default="mid.wav", help="First file from samples/")
    p.add_argument("--file2", default="realistic.mp3", help="Second file from samples/")
    p.add_argument("--pause-s", type=float, default=3.0, help="Artificial silence seconds between segments")
    p.add_argument("--debug", action="store_true", help="Verbose debug logs")
    p.add_argument("--full-text", action="store_true", help="Print full combined text (no truncation)")
    p.add_argument("--voxtral-key", type=str, default=None, help="API key (overrides VOXTRAL_API_KEY env)")
    return p.parse_args()


async def run(args: argparse.Namespace) -> None:
    apply_key_overrides(args.voxtral_key)

    def resolve_sample(name: str) -> str | None:
        return find_sample_by_name(name)

    f1 = resolve_sample(args.file1)
    f2 = resolve_sample(args.file2)
    if not f1:
        print_file_not_found(args.file1, str(SAMPLES_DIR), find_sample_files())
        return
    if not f2:
        print_file_not_found(args.file2, str(SAMPLES_DIR), find_sample_files())
        return

    pcm1 = file_to_pcm16_mono_16k(f1)
    pcm2 = file_to_pcm16_mono_16k(f2)
    dur1 = file_duration_seconds(f1)
    dur2 = file_duration_seconds(f2)

    print(f"\n{section_header('CONVERSATION TEST')}")
    print(dim(f"  server: {args.server}"))
    print(dim(f"  file1: {os.path.basename(f1)}  file2: {os.path.basename(f2)}"))
    print(dim(f"  pause: {args.pause_s}s"))
    print()

    client = ConvoClient(args.server, args.secure, debug=args.debug)
    res = await client.run_convo(pcm1, dur1, pcm2, dur2, args.pause_s, debug=args.debug)

    print_transcript_line(res.get("text", ""), full=args.full_text, truncate=120)
    print_convo_metrics(client, res)


def main() -> None:
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
