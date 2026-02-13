"""Main FastAPI server for Voxtral Realtime STT (vLLM)."""

from __future__ import annotations

import logging
import contextlib
import multiprocessing

with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("spawn", force=True)

from src.scripts.filters import configure as configure_log_filters  # noqa: E402

configure_log_filters()

from fastapi import FastAPI, WebSocket  # noqa: E402
from fastapi.responses import ORJSONResponse  # noqa: E402

from src.runtime.logging import configure_logging  # noqa: E402
from src.runtime.dependencies import build_runtime_deps  # noqa: E402
from src.handlers.websocket import handle_websocket_connection  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(default_response_class=ORJSONResponse)

configure_logging()


@app.on_event("startup")
async def preload_engines() -> None:
    runtime_deps = await build_runtime_deps()
    app.state.runtime_deps = runtime_deps
    logger.info("runtime: ready")


@app.on_event("shutdown")
async def stop_engines() -> None:
    runtime_deps = getattr(app.state, "runtime_deps", None)
    if runtime_deps is not None:
        await runtime_deps.shutdown()


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    runtime_deps = getattr(app.state, "runtime_deps", None)
    if runtime_deps is None:
        raise RuntimeError("Runtime dependencies are not initialized")
    await handle_websocket_connection(websocket, runtime_deps)
