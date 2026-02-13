#!/usr/bin/env python3
"""Idle timeout test for the STT server.

Opens a WebSocket connection, sends nothing, and waits for server-initiated close.
"""

from __future__ import annotations

import os
import asyncio
import logging
import argparse

import config
from client import IdleClient
from utils.env import apply_key_overrides, derive_default_server
from data.printing import dim, format_fail, format_info, format_pass, format_error, section_header

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test server idle timeout behavior")

    default_server = derive_default_server()
    parser.add_argument("--server", type=str, default=default_server, help="host:port or ws://host:port or full URL")
    parser.add_argument("--secure", action="store_true", help="Use WSS")
    parser.add_argument(
        "--grace-period",
        type=float,
        default=config.IDLE_GRACE_PERIOD_S,
        help="Grace period in seconds added to idle timeout",
    )
    parser.add_argument("--debug", action="store_true", help="Print debug info including connection events")
    parser.add_argument("--voxtral-key", type=str, default=None, help="API key (overrides VOXTRAL_API_KEY env)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING, format="%(levelname)s: %(message)s")

    apply_key_overrides(args.voxtral_key)

    api_key = os.getenv(config.ENV_VOXTRAL_API_KEY)
    if not api_key:
        print(format_error("API key missing", f"use --voxtral-key or set {config.ENV_VOXTRAL_API_KEY}"))
        return 1

    idle_timeout = config.SERVER_IDLE_TIMEOUT_S
    total_wait = idle_timeout + args.grace_period

    print(f"\n{section_header('IDLE TIMEOUT TEST')}")
    print(dim(f"  server: {args.server}"))
    print(dim(f"  idle timeout: {idle_timeout:.0f}s"))
    print(dim(f"  grace period: {args.grace_period:.1f}s"))
    print(dim(f"  max wait: {total_wait:.1f}s"))
    print()

    client = IdleClient(args.server, args.secure, debug=args.debug)
    result = asyncio.run(client.run(total_wait))

    if result.success:
        print(format_pass("Server closed idle connection"))
        print(format_info(f"elapsed: {result.elapsed_s:.1f}s"))
        if result.close_code is not None:
            print(format_info(f"close code: {result.close_code}"))
        if result.close_reason:
            print(format_info(f"close reason: {result.close_reason}"))
        return 0

    print(format_fail("Idle timeout test", result.error or "unknown error"))
    print(format_info(f"elapsed: {result.elapsed_s:.1f}s"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
