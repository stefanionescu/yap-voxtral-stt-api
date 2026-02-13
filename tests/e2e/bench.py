#!/usr/bin/env python3
"""Concurrent benchmark runner for Voxtral /ws streaming."""

from __future__ import annotations

import os
import sys
import uuid
import asyncio
import logging
import secrets
import argparse
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.client import RealtimeClient  # noqa: E402
from tests.params.env import derive_default_server  # noqa: E402
from tests.data.printing.summary import print_benchmark_summary  # noqa: E402
from tests.data.printing import dim, format_error, section_header  # noqa: E402
from tests.utils import (  # noqa: E402
    make_silence_pcm16,
    find_sample_by_name,
    file_duration_seconds,
    file_to_pcm16_mono_16k,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark Voxtral /ws concurrency")
    p.add_argument("--server", default=derive_default_server(), help="host:port or ws://host:port")
    p.add_argument("--secure", action="store_true")
    p.add_argument("--requests", type=int, default=32)
    p.add_argument("--concurrency", type=int, default=32)
    p.add_argument("--rtf", type=float, default=2.0)
    p.add_argument("--file", default="mid.wav", help="Audio file name in samples/ or absolute path")
    p.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout (seconds)")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    if not os.getenv("VOXTRAL_API_KEY"):
        print(format_error("VOXTRAL_API_KEY missing", "set VOXTRAL_API_KEY for test clients"))
        return 1

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
            pcm = make_silence_pcm16(2.0)
            audio_duration_s = 2.0

    total_reqs = max(1, int(args.requests))
    concurrency = max(1, int(args.concurrency))

    print(f"\n{section_header('BENCH')}")
    print(dim(f"  server: {args.server}"))
    print(dim(f"  requests: {total_reqs}"))
    print(dim(f"  concurrency: {concurrency}"))
    print(dim(f"  rtf: {args.rtf}"))
    print(dim(f"  audio: {audio_duration_s:.2f}s"))
    print()

    sem = asyncio.Semaphore(concurrency)
    results: list[dict[str, float]] = []
    rejected = 0
    errors = 0

    async def worker(i: int) -> None:
        nonlocal rejected, errors
        async with sem:
            # Stagger starts to avoid a thundering herd.
            await asyncio.sleep(secrets.randbelow(200) / 1000.0)

            client = RealtimeClient(args.server, args.secure, debug=args.debug)
            session_id = f"bench-{uuid.uuid4()}"
            request_id = f"utt-{uuid.uuid4()}"
            res = await client.run_stream(
                pcm,
                session_id=session_id,
                request_id=request_id,
                rtf=args.rtf,
                timeout_s=float(args.timeout),
            )
            if res.error:
                if "server_at_capacity" in res.error:
                    rejected += 1
                else:
                    errors += 1
            else:
                results.append(res.metrics)

    tasks = [asyncio.create_task(worker(i)) for i in range(total_reqs)]
    await asyncio.gather(*tasks, return_exceptions=True)

    if rejected or errors:
        print(dim(f"  rejected(capacity): {rejected}"))
        print(dim(f"  errors: {errors}"))
        print()

    print_benchmark_summary("Voxtral Bench", results)

    return 0 if errors == 0 else 2


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING, format="%(levelname)s: %(message)s")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
