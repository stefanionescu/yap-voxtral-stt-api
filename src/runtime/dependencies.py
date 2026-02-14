"""Runtime dependency construction (vLLM realtime + admission control)."""

from __future__ import annotations

import logging

from src.state import RuntimeDeps
from src.realtime.bridge import RealtimeBridge
from src.handlers.connections import ConnectionManager
from src.state.settings import AppSettings, LimitsSettings

from .settings import load_settings
from .vllm import build_vllm_realtime

logger = logging.getLogger(__name__)


async def build_runtime_deps() -> RuntimeDeps:
    settings: AppSettings = load_settings()

    engine_stack, _engine_client, _serving_models, serving_realtime, tuned_settings = await build_vllm_realtime(
        settings
    )

    realtime_bridge = RealtimeBridge(
        serving_realtime=serving_realtime,
        allowed_model_name=tuned_settings.model.served_model_name,
    )

    max_connections = tuned_settings.limits.max_concurrent_connections
    if max_connections <= 0:
        # Auto: default to vLLM's tuned sequence capacity.
        max_connections = int(tuned_settings.vllm.max_num_seqs)

    tuned_settings = AppSettings(
        auth=tuned_settings.auth,
        limits=LimitsSettings(
            max_concurrent_connections=max_connections,
        ),
        websocket=tuned_settings.websocket,
        model=tuned_settings.model,
        vllm=tuned_settings.vllm,
    )

    connections = ConnectionManager(max_connections=tuned_settings.limits.max_concurrent_connections)

    return RuntimeDeps(
        connections=connections,
        realtime_bridge=realtime_bridge,
        settings=tuned_settings,
        _engine_stack=engine_stack,
    )


__all__ = ["RuntimeDeps", "build_runtime_deps"]
