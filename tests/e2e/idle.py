#!/usr/bin/env python3
"""Idle timeout test for the Voxtral /ws server."""

from __future__ import annotations

import sys
import time
import asyncio
import logging
import argparse
from pathlib import Path

import websockets

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.params.env import build_ws_url, resolve_api_key, derive_default_server  # noqa: E402
from tests.data.printing import dim, format_info, format_pass, format_error, section_header  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test server idle timeout behavior")
    p.add_argument("--server", default=derive_default_server(), help="host:port or ws://host:port")
    p.add_argument("--secure", action="store_true")
    p.add_argument("--idle-expect-seconds", type=float, default=150.0)
    p.add_argument("--idle-grace-seconds", type=float, default=15.0)
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    api_key = resolve_api_key()
    if not api_key:
        print(format_error("VOXTRAL_API_KEY missing", "set VOXTRAL_API_KEY for test clients"))
        return 1

    ws_url = build_ws_url(args.server, secure=args.secure, api_key=api_key)
    total_wait = max(1.0, args.idle_expect_seconds + args.idle_grace_seconds)

    print(f"\n{section_header('IDLE TIMEOUT')}")
    print(dim(f"  ws: {ws_url}"))
    print(dim(f"  expect idle: {args.idle_expect_seconds:.0f}s (+{args.idle_grace_seconds:.0f}s grace)"))
    print()

    t0 = time.perf_counter()
    try:
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as ws:
            if args.debug:
                print(format_info("connected, waiting for server close..."))
            try:
                await asyncio.wait_for(ws.recv(), timeout=total_wait)
                print(format_error("Unexpected message", "server sent data while idle"))
                return 2
            except TimeoutError:
                print(format_error("Timeout", f"server did not close within {total_wait:.0f}s"))
                return 2
    except websockets.exceptions.ConnectionClosed as exc:
        elapsed = time.perf_counter() - t0
        print(format_pass(f"Server closed idle connection in {elapsed:.1f}s"))
        print(format_info(f"close code: {exc.code}"))
        if exc.reason:
            print(format_info(f"close reason: {exc.reason}"))
        if exc.code != 4000:
            print(format_error("Unexpected close code", f"expected 4000, got {exc.code}"))
            return 2
        return 0


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING, format="%(levelname)s: %(message)s")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
