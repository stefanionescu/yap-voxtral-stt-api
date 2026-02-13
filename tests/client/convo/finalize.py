from __future__ import annotations

import json
import time
import asyncio
from contextlib import suppress

import config


async def wait_for_done(handler, ws, *, session_id: str, request_id: str, timeout_s: float) -> None:
    done = handler.done_event

    async def app_ping_loop() -> None:
        try:
            while not done.is_set():
                await asyncio.sleep(config.WS_APP_PING_INTERVAL_S)
                if done.is_set():
                    return
                msg = {
                    config.PROTO_KEY_TYPE: config.PROTO_TYPE_PING,
                    config.PROTO_KEY_SESSION_ID: session_id,
                    config.PROTO_KEY_REQUEST_ID: request_id,
                    config.PROTO_KEY_PAYLOAD: {},
                }
                await ws.send(json.dumps(msg))
        except Exception:
            return

    ping_task = asyncio.create_task(app_ping_loop()) if config.WS_APP_PING_INTERVAL_S > 0 else None
    try:
        async with asyncio.timeout(timeout_s):
            await done.wait()
    except TimeoutError:
        if getattr(handler, "error", None) is None:
            handler.error = f"timeout waiting for transcription.done (>{timeout_s:.1f}s)"
        handler.done_event.set()
    finally:
        if ping_task is not None:
            ping_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await ping_task


async def close_ws_gracefully(ws, base) -> None:
    close_start = time.perf_counter()
    with suppress(Exception):
        await ws.close(code=config.WS_CLOSE_CODE_NORMAL)
    base.close_elapsed_s = time.perf_counter() - close_start


__all__ = ["close_ws_gracefully", "wait_for_done"]
