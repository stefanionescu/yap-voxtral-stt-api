#!/usr/bin/env python3
"""Interactive client for Voxtral /ws (manual debugging)."""

from __future__ import annotations

import sys
import json
import uuid
import asyncio
import argparse
import contextlib
from pathlib import Path

import websockets

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.params.env import build_ws_url, resolve_api_key, derive_default_server  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Interactive Voxtral /ws client")
    p.add_argument("--server", default=derive_default_server())
    p.add_argument("--secure", action="store_true")
    return p.parse_args()


async def _recv_printer(ws) -> None:
    while True:
        raw = await ws.recv()
        print(f"<< {raw}")


async def _read_stdin_line() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)


async def _interactive_send_loop(ws, *, session_id: str, request_id: str) -> None:
    while True:
        line = await _read_stdin_line()
        if not line:
            return
        line = line.strip()
        if not line:
            continue

        if line == "/ping":
            msg = {
                "type": "ping",
                "session_id": session_id,
                "request_id": f"ping-{uuid.uuid4()}",
                "payload": {},
            }
            await ws.send(json.dumps(msg))
            continue

        if line == "/start":
            msg = {
                "type": "input_audio_buffer.commit",
                "session_id": session_id,
                "request_id": request_id,
                "payload": {"final": False},
            }
            await ws.send(json.dumps(msg))
            continue

        if line == "/final":
            msg = {
                "type": "input_audio_buffer.commit",
                "session_id": session_id,
                "request_id": request_id,
                "payload": {"final": True},
            }
            await ws.send(json.dumps(msg))
            continue

        if line == "/end":
            msg = {"type": "end", "session_id": session_id, "request_id": f"end-{uuid.uuid4()}", "payload": {}}
            await ws.send(json.dumps(msg))
            return

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            print("invalid json; use /ping /start /final /end or a JSON envelope")
            continue
        await ws.send(json.dumps(msg))


async def run(args: argparse.Namespace) -> int:
    api_key = resolve_api_key()
    if not api_key:
        print("VOXTRAL_API_KEY missing")
        return 1
    ws_url = build_ws_url(args.server, secure=args.secure, api_key=api_key)
    session_id = f"live-{uuid.uuid4()}"
    request_id = f"utt-{uuid.uuid4()}"

    print(f"ws: {ws_url}")
    print("Commands:")
    print("  /ping")
    print("  /start  (commit final=false)")
    print("  /final  (commit final=true)")
    print("  /end")
    print("  JSON line (sent as-is envelope)")

    async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as ws:
        task = asyncio.create_task(_recv_printer(ws))
        try:
            await _interactive_send_loop(ws, session_id=session_id, request_id=request_id)
        finally:
            task.cancel()
            with contextlib.suppress(Exception):
                await task

    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
