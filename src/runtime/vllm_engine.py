"""vLLM realtime engine bootstrap."""

from __future__ import annotations

import inspect
import logging
import contextlib
from typing import Any

from src.config.models import VOXTRAL_MODEL_DIR, VOXTRAL_SERVED_MODEL_NAME
from src.config.vllm import (
    VLLM_DTYPE,
    VLLM_LOAD_FORMAT,
    VLLM_MAX_NUM_SEQS,
    VLLM_CONFIG_FORMAT,
    VLLM_ENFORCE_EAGER,
    VLLM_MAX_MODEL_LEN,
    VLLM_KV_CACHE_DTYPE,
    VLLM_TOKENIZER_MODE,
    VLLM_COMPILATION_CONFIG,
    VLLM_DISABLE_COMPILE_CACHE,
    VLLM_GPU_MEMORY_UTILIZATION,
    VLLM_MAX_NUM_BATCHED_TOKENS,
)

from .model import ensure_voxtral_snapshot

logger = logging.getLogger(__name__)


def _filter_kwargs(cls: type[Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter kwargs to those accepted by cls' constructor."""
    sig = inspect.signature(cls)
    accepted = set(sig.parameters.keys())
    return {k: v for k, v in kwargs.items() if k in accepted and v is not None}


async def build_vllm_realtime() -> tuple[Any, Any, Any, Any]:
    """Create (engine_stack, engine_client, serving_models, serving_realtime)."""

    # Ensure a writable local snapshot exists and tekken.json delay is patched.
    VOXTRAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_dir = ensure_voxtral_snapshot()

    from vllm.usage.usage_lib import UsageContext  # noqa: PLC0415
    from vllm.engine.arg_utils import AsyncEngineArgs  # noqa: PLC0415
    from vllm.entrypoints.openai.models.protocol import BaseModelPath  # noqa: PLC0415
    from vllm.entrypoints.openai.models.serving import OpenAIServingModels  # noqa: PLC0415
    from vllm.entrypoints.openai.realtime.serving import OpenAIServingRealtime  # noqa: PLC0415
    from vllm.entrypoints.openai.api_server import build_async_engine_client_from_engine_args  # noqa: PLC0415

    engine_args_kwargs: dict[str, Any] = {
        "model": str(model_dir),
        "dtype": VLLM_DTYPE,
        "gpu_memory_utilization": VLLM_GPU_MEMORY_UTILIZATION,
        "max_model_len": VLLM_MAX_MODEL_LEN,
        "max_num_seqs": VLLM_MAX_NUM_SEQS,
        "max_num_batched_tokens": VLLM_MAX_NUM_BATCHED_TOKENS,
        "enforce_eager": VLLM_ENFORCE_EAGER,
        "kv_cache_dtype": VLLM_KV_CACHE_DTYPE,
        "tokenizer_mode": VLLM_TOKENIZER_MODE,
        "config_format": VLLM_CONFIG_FORMAT,
        "load_format": VLLM_LOAD_FORMAT,
        "disable_compile_cache": VLLM_DISABLE_COMPILE_CACHE,
        "compilation_config": VLLM_COMPILATION_CONFIG,
        "served_model_name": VOXTRAL_SERVED_MODEL_NAME,
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
            name=VOXTRAL_SERVED_MODEL_NAME,
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
