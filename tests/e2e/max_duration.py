#!/usr/bin/env python3
"""Max connection duration test for the Voxtral /ws server.

Note: The server also enforces an idle timeout (default: 150s). This client sends
explicit {"type":"ping"} envelopes to keep the connection alive until the max
duration close fires.
"""

from __future__ import annotations

import sys
import json
import time
import uuid
import asyncio
import logging
import argparse
import contextlib
from pathlib import Path

import websockets

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.params.env import build_ws_url, resolve_api_key, derive_default_server  # noqa: E402
from tests.data.printing import dim, format_info, format_pass, format_error, section_header  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test server max connection duration behavior")
    p.add_argument("--server", default=derive_default_server(), help="host:port or ws://host:port")
    p.add_argument("--secure", action="store_true")
    p.add_argument("--expect-seconds", type=float, default=5400.0)
    p.add_argument("--grace-seconds", type=float, default=30.0)
    p.add_argument("--ping-every-seconds", type=float, default=30.0)
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    api_key = resolve_api_key()
    if not api_key:
        print(format_error("VOXTRAL_API_KEY missing", "set VOXTRAL_API_KEY for test clients"))
        return 1

    ws_url = build_ws_url(args.server, secure=args.secure, api_key=api_key)
    total_wait = max(1.0, args.expect_seconds + args.grace_seconds)
    session_id = f"max-duration-{uuid.uuid4()}"

    print(f"\n{section_header('MAX DURATION')}")
    print(dim(f"  ws: {ws_url}"))
    print(dim(f"  expect close: {args.expect_seconds:.0f}s (+{args.grace_seconds:.0f}s grace)"))
    print(dim(f"  keepalive ping every: {args.ping_every_seconds:.0f}s"))
    print()

    async def keepalive(ws) -> None:
        while True:
            await asyncio.sleep(max(0.5, float(args.ping_every_seconds)))
            msg = {
                "type": "ping",
                "session_id": session_id,
                "request_id": f"ping-{uuid.uuid4()}",
                "payload": {},
            }
            await ws.send(json.dumps(msg))

    t0 = time.perf_counter()
    keepalive_task: asyncio.Task | None = None
    try:
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as ws:
            keepalive_task = asyncio.create_task(keepalive(ws))
            deadline = t0 + total_wait
            while True:
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    print(format_error("Timeout", f"server did not close within {total_wait:.0f}s"))
                    return 2
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except TimeoutError:
                    print(format_error("Timeout", f"server did not close within {total_wait:.0f}s"))
                    return 2

                if args.debug:
                    # Expect pongs; ignore any server traffic until close.
                    print(format_info(f"recv: {msg[:200]}"))
    except websockets.exceptions.ConnectionClosed as exc:
        elapsed = time.perf_counter() - t0
        print(format_pass(f"Server closed connection in {elapsed:.1f}s"))
        print(format_info(f"close code: {exc.code}"))
        if exc.reason:
            print(format_info(f"close reason: {exc.reason}"))
        if exc.code != 4003:
            print(format_error("Unexpected close code", f"expected 4003, got {exc.code}"))
            return 2
        return 0
    finally:
        if keepalive_task is not None:
            keepalive_task.cancel()
            with contextlib.suppress(Exception):
                await keepalive_task


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING, format="%(levelname)s: %(message)s")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
