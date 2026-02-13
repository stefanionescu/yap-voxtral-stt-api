"""Main FastAPI server for Voxtral Realtime STT (vLLM)."""

from __future__ import annotations

import logging
import multiprocessing
from contextlib import suppress, asynccontextmanager

with suppress(RuntimeError):
    multiprocessing.set_start_method("spawn", force=True)

from fastapi import FastAPI, WebSocket  # noqa: E402
from fastapi.responses import ORJSONResponse  # noqa: E402

from src.config.websocket import WS_ENDPOINT_PATH  # noqa: E402
from src.runtime.logging import configure_logging  # noqa: E402
from src.runtime.dependencies import build_runtime_deps  # noqa: E402
from src.handlers.websocket.manager import handle_websocket_connection  # noqa: E402

logger = logging.getLogger(__name__)

configure_logging()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    runtime_deps = await build_runtime_deps()
    app.state.runtime_deps = runtime_deps
    logger.info("runtime: ready")
    try:
        yield
    finally:
        deps = getattr(app.state, "runtime_deps", None)
        if deps is not None:
            await deps.shutdown()


app = FastAPI(default_response_class=ORJSONResponse, lifespan=_lifespan)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket(WS_ENDPOINT_PATH)
async def websocket_endpoint(websocket: WebSocket) -> None:
    runtime_deps = getattr(app.state, "runtime_deps", None)
    if runtime_deps is None:
        raise RuntimeError("Runtime dependencies are not initialized")
    await handle_websocket_connection(websocket, runtime_deps)
