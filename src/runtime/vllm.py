"""vLLM realtime engine bootstrap."""

from __future__ import annotations

import inspect
import logging
import contextlib
from typing import Any

from vllm.usage.usage_lib import UsageContext
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.entrypoints.openai.models.protocol import BaseModelPath
from vllm.entrypoints.openai.models.serving import OpenAIServingModels
from vllm.entrypoints.openai.realtime.serving import OpenAIServingRealtime
from vllm.entrypoints.openai.api_server import build_async_engine_client_from_engine_args

from src.state.settings import AppSettings

from .model import ensure_voxtral_snapshot

logger = logging.getLogger(__name__)


def _filter_kwargs(cls: type[Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter kwargs to those accepted by cls' constructor."""
    sig = inspect.signature(cls)
    accepted = set(sig.parameters.keys())
    return {k: v for k, v in kwargs.items() if k in accepted and v is not None}


async def build_vllm_realtime(settings: AppSettings) -> tuple[Any, Any, Any, Any]:
    """Create (engine_stack, engine_client, serving_models, serving_realtime)."""

    # Ensure a writable local snapshot exists and tekken.json delay is patched.
    settings.model.model_dir.mkdir(parents=True, exist_ok=True)
    model_dir = ensure_voxtral_snapshot(settings.model)

    engine_args_kwargs: dict[str, Any] = {
        "model": str(model_dir),
        "dtype": settings.vllm.dtype,
        "gpu_memory_utilization": settings.vllm.gpu_memory_utilization,
        "max_model_len": settings.vllm.max_model_len,
        "max_num_seqs": settings.vllm.max_num_seqs,
        "max_num_batched_tokens": settings.vllm.max_num_batched_tokens,
        "enforce_eager": settings.vllm.enforce_eager,
        "kv_cache_dtype": settings.vllm.kv_cache_dtype,
        "tokenizer_mode": settings.vllm.tokenizer_mode,
        "config_format": settings.vllm.config_format,
        "load_format": settings.vllm.load_format,
        "disable_compile_cache": settings.vllm.disable_compile_cache,
        "compilation_config": settings.vllm.compilation_config,
        "served_model_name": settings.model.served_model_name,
        "trust_remote_code": False,
    }

    engine_args = AsyncEngineArgs(**_filter_kwargs(AsyncEngineArgs, engine_args_kwargs))

    logger.info("vllm: building engine (model=%s)", model_dir)
    engine_stack = contextlib.AsyncExitStack()
    engine_cm = build_async_engine_client_from_engine_args(
        engine_args,
        usage_context=UsageContext.OPENAI_API_SERVER,
    )
    engine_client = await engine_stack.enter_async_context(engine_cm)

    base_model_paths = [
        BaseModelPath(
            name=settings.model.served_model_name,
            model_path=str(model_dir),
        )
    ]
    serving_models = OpenAIServingModels(engine_client, base_model_paths)
    if hasattr(serving_models, "init_static_loras"):
        maybe = serving_models.init_static_loras
        res = maybe()
        if inspect.isawaitable(res):
            await res

    serving_realtime = OpenAIServingRealtime(
        engine_client,
        serving_models,
        request_logger=None,
    )

    return engine_stack, engine_client, serving_models, serving_realtime


__all__ = ["build_vllm_realtime"]
