"""Runtime dependency construction (vLLM realtime + admission control)."""

from __future__ import annotations

import logging

from src.state import RuntimeDeps
from src.state.settings import AppSettings
from src.realtime.bridge import RealtimeBridge
from src.handlers.connections import ConnectionManager

from .vllm import build_vllm_realtime
from .settings_loader import load_settings

logger = logging.getLogger(__name__)


async def build_runtime_deps() -> RuntimeDeps:
    settings: AppSettings = load_settings()

    connections = ConnectionManager(max_connections=settings.limits.max_concurrent_connections)
    engine_stack, _engine_client, _serving_models, serving_realtime = await build_vllm_realtime(settings)

    realtime_bridge = RealtimeBridge(
        serving_realtime=serving_realtime,
        allowed_model_name=settings.model.served_model_name,
    )

    return RuntimeDeps(
        connections=connections,
        realtime_bridge=realtime_bridge,
        settings=settings,
        _engine_stack=engine_stack,
    )


__all__ = ["RuntimeDeps", "build_runtime_deps"]
