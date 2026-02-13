#!/usr/bin/env python3
"""Benchmark WebSocket streaming for the STT server."""

from __future__ import annotations

import os
import time
import asyncio
import argparse

from tests import config
from tests.client import BenchmarkRunner
from tests.utils.env import apply_key_overrides, derive_default_server
from tests.data.printing import dim, red, format_error, section_header, print_benchmark_summary
from tests.utils import (
    SAMPLES_DIR,
    find_sample_files,
    find_sample_by_name,
    print_file_not_found,
    file_to_pcm16_mono_16k,
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="WebSocket streaming benchmark")

    ap.add_argument("--server", default=derive_default_server(), help="host:port or ws://host:port or full URL")
    ap.add_argument("--secure", action="store_true")
    ap.add_argument("--n", type=int, default=20, help="Total sessions")
    ap.add_argument("--concurrency", type=int, default=5, help="Max concurrent sessions")
    ap.add_argument("--file", type=str, default="mid.wav", help="Audio file from samples/")
    ap.add_argument("--voxtral-key", type=str, default=None, help="API key (overrides VOXTRAL_API_KEY env)")
    ap.add_argument("--debug", action="store_true", help="Print debug info including error details")
    return ap.parse_args()


def run(args: argparse.Namespace) -> None:
    file_path = find_sample_by_name(args.file)
    if not file_path:
        print_file_not_found(args.file, str(SAMPLES_DIR), find_sample_files())
        return

    apply_key_overrides(args.voxtral_key)

    if not os.getenv(config.ENV_VOXTRAL_API_KEY):
        print(format_error("API key missing", f"use --voxtral-key or set {config.ENV_VOXTRAL_API_KEY}"))
        return

    print(f"\n{section_header('BENCHMARK')}")
    print(dim(f"  server: {args.server}"))
    print(dim(f"  file: {os.path.basename(file_path)}"))
    print(dim(f"  n={args.n}  concurrency={args.concurrency}"))
    print()

    pcm = file_to_pcm16_mono_16k(file_path)
    runner = BenchmarkRunner(args.server, args.secure, debug=args.debug)

    start = time.time()
    results, rejected, errors = asyncio.run(runner.run_benchmark(pcm, args.n, args.concurrency))
    elapsed = time.time() - start

    print_benchmark_summary("WebSocket Streaming", results)
    print(f"Rejected: {red(str(rejected)) if rejected else rejected}")
    print(f"Errors: {red(str(errors)) if errors else errors}")
    print(f"Total elapsed: {elapsed:.4f}s")

    if results:
        total_audio = sum(r["audio_s"] for r in results)
        print(f"Total audio processed: {total_audio:.2f}s")
        overall = total_audio / elapsed if elapsed > 0 else 0.0
        overall_min = overall * 60.0
        print(f"Overall throughput: {overall_min:.2f} sec/min = {overall:.2f} min/min")


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
