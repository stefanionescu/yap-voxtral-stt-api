from __future__ import annotations

import time
import asyncio
from contextlib import suppress

import config


async def wait_for_done(handler, ws, *, session_id: str, request_id: str, timeout_s: float) -> None:
    done = handler.done_event
    try:
        async with asyncio.timeout(timeout_s):
            await done.wait()
    except TimeoutError:
        if getattr(handler, "error", None) is None:
            handler.error = f"timeout waiting for transcription.done (>{timeout_s:.1f}s)"
        handler.done_event.set()


async def close_ws_gracefully(ws, base) -> None:
    close_start = time.perf_counter()
    with suppress(Exception):
        await ws.close(code=config.WS_CLOSE_CODE_NORMAL)
    base.close_elapsed_s = time.perf_counter() - close_start


__all__ = ["close_ws_gracefully", "wait_for_done"]
