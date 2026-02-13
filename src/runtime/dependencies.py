"""Runtime dependency construction (vLLM realtime + admission control)."""

from __future__ import annotations

import logging

from src.state import RuntimeDeps
from src.realtime.bridge import RealtimeBridge
from src.handlers.connections import ConnectionManager
from src.config.models import VOXTRAL_SERVED_MODEL_NAME
from src.config.limits import MAX_CONCURRENT_CONNECTIONS

from .vllm_engine import build_vllm_realtime

logger = logging.getLogger(__name__)


async def build_runtime_deps() -> RuntimeDeps:
    connections = ConnectionManager(max_connections=MAX_CONCURRENT_CONNECTIONS)
    engine_stack, _engine_client, _serving_models, serving_realtime = await build_vllm_realtime()

    realtime_bridge = RealtimeBridge(
        serving_realtime=serving_realtime,
        allowed_model_name=VOXTRAL_SERVED_MODEL_NAME,
    )

    return RuntimeDeps(
        connections=connections,
        realtime_bridge=realtime_bridge,
        _engine_stack=engine_stack,
    )


__all__ = ["RuntimeDeps", "build_runtime_deps"]
