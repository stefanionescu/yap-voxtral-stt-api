"""vLLM realtime engine bootstrap."""

from __future__ import annotations

import os
import json
import shutil
import inspect
import logging
import contextlib
from typing import Any
from pathlib import Path
import subprocess  # noqa: S404

from vllm.usage.usage_lib import UsageContext
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.entrypoints.openai.models.protocol import BaseModelPath
from vllm.entrypoints.openai.models.serving import OpenAIServingModels
from vllm.entrypoints.openai.realtime.serving import OpenAIServingRealtime
from vllm.entrypoints.openai.api_server import build_async_engine_client_from_engine_args

from src.state.settings import AppSettings, VllmSettings

from .model import ensure_voxtral_snapshot

logger = logging.getLogger(__name__)

TUNING_KV_BUDGET_FRACTION: float = 0.90  # leave headroom for weights, activations, fragmentation
TUNING_MAX_NUM_SEQS_CAP: int = 512


def _filter_kwargs(cls: type[Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter kwargs to those accepted by cls' constructor."""
    sig = inspect.signature(cls)
    accepted = set(sig.parameters.keys())
    return {k: v for k, v in kwargs.items() if k in accepted and v is not None}


def _env_is_set(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _read_mistral_params(model_dir: Path) -> tuple[int, int] | None:
    params_path = model_dir / "params.json"
    result: tuple[int, int] | None = None
    if not params_path.exists():
        return result

    doc: Any | None
    try:
        doc = json.loads(params_path.read_text(encoding="utf-8"))
    except Exception:
        doc = None

    if isinstance(doc, dict):
        dim = doc.get("dim") or doc.get("hidden_size") or doc.get("d_model")
        n_layers = doc.get("n_layers") or doc.get("num_hidden_layers") or doc.get("num_layers")
        if dim is not None and n_layers is not None:
            try:
                dim_i = int(dim)
                layers_i = int(n_layers)
            except Exception:
                dim_i = 0
                layers_i = 0
            if dim_i > 0 and layers_i > 0:
                result = (dim_i, layers_i)

    return result


def _sum_safetensors_bytes(model_dir: Path) -> int:
    total = 0
    for p in model_dir.glob("*.safetensors"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def _detect_total_gpu_memory_bytes() -> int | None:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None

    try:
        proc = subprocess.run(  # noqa: S603
            [nvidia_smi, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None

    # memory.total is reported in MiB when using `nounits`.
    first = lines[0].split(",")[0].strip()
    try:
        mib = int(first)
    except Exception:
        return None
    return mib * 1024 * 1024


def _kv_cache_bytes_per_element(*, kv_cache_dtype: str, model_dtype: str) -> int:
    dt = (kv_cache_dtype or "").strip().lower()
    bytes_per_el = 2

    if dt.startswith("fp8") or dt in {"int8", "uint8"}:
        bytes_per_el = 1
    elif dt in {"fp16", "float16", "half", "bf16", "bfloat16"}:
        bytes_per_el = 2
    elif dt == "auto":
        # Conservative: assume FP16/BF16 when auto-tuning.
        bytes_per_el = 2
    else:
        md = (model_dtype or "").strip().lower()
        if md in {"bf16", "bfloat16", "fp16", "float16", "half"}:
            bytes_per_el = 2

    return bytes_per_el


def _estimate_max_num_seqs(settings: AppSettings, model_dir: Path) -> int | None:
    gpu_total = _detect_total_gpu_memory_bytes()
    if not gpu_total:
        return None

    arch = _read_mistral_params(model_dir)
    if arch is None:
        return None
    dim, n_layers = arch

    weights_bytes = _sum_safetensors_bytes(model_dir)

    kv_bytes = _kv_cache_bytes_per_element(
        kv_cache_dtype=settings.vllm.kv_cache_dtype,
        model_dtype=settings.vllm.dtype,
    )

    # Approx KV bytes/token = (K + V) * layers * dim * bytes_per_elem
    # where K and V are each `dim` elements per layer.
    per_token_bytes = 2 * n_layers * dim * kv_bytes
    per_seq_bytes = int(per_token_bytes) * int(max(1, settings.vllm.max_model_len))
    if per_seq_bytes <= 0:
        return None

    budget = int(gpu_total * float(settings.vllm.gpu_memory_utilization))
    budget -= int(weights_bytes)
    budget = int(max(0, budget) * float(TUNING_KV_BUDGET_FRACTION))
    if budget <= 0:
        return None

    est = int(max(1, budget // per_seq_bytes))
    return max(1, min(TUNING_MAX_NUM_SEQS_CAP, est))


def _tune_max_num_seqs(settings: AppSettings, model_dir: Path) -> int:
    max_num_seqs = settings.vllm.max_num_seqs
    if _env_is_set("VLLM_MAX_NUM_SEQS"):
        return max_num_seqs

    recommended = _estimate_max_num_seqs(settings, model_dir)
    if recommended is None:
        logger.info("vllm: using configured max_num_seqs=%s (no tuning data)", max_num_seqs)
        return max_num_seqs

    logger.info("vllm: tuned max_num_seqs=%s", recommended)
    return recommended


def _build_engine_args(settings: AppSettings, model_dir: Path, *, max_num_seqs: int) -> AsyncEngineArgs:
    engine_args_kwargs: dict[str, Any] = {
        "model": str(model_dir),
        "dtype": settings.vllm.dtype,
        "gpu_memory_utilization": settings.vllm.gpu_memory_utilization,
        "max_model_len": settings.vllm.max_model_len,
        "max_num_seqs": int(max(1, max_num_seqs)),
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
    return AsyncEngineArgs(**_filter_kwargs(AsyncEngineArgs, engine_args_kwargs))


async def _build_serving_models(engine_client: Any, settings: AppSettings, model_dir: Path) -> OpenAIServingModels:
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
    return serving_models


def _with_vllm_max_num_seqs(settings: AppSettings, *, max_num_seqs: int) -> AppSettings:
    if max_num_seqs == settings.vllm.max_num_seqs:
        return settings

    tuned_vllm = VllmSettings(
        dtype=settings.vllm.dtype,
        gpu_memory_utilization=settings.vllm.gpu_memory_utilization,
        max_model_len=settings.vllm.max_model_len,
        max_num_seqs=max_num_seqs,
        max_num_batched_tokens=settings.vllm.max_num_batched_tokens,
        enforce_eager=settings.vllm.enforce_eager,
        kv_cache_dtype=settings.vllm.kv_cache_dtype,
        tokenizer_mode=settings.vllm.tokenizer_mode,
        config_format=settings.vllm.config_format,
        load_format=settings.vllm.load_format,
        compilation_config=settings.vllm.compilation_config,
        disable_compile_cache=settings.vllm.disable_compile_cache,
    )
    return AppSettings(
        auth=settings.auth,
        limits=settings.limits,
        websocket=settings.websocket,
        model=settings.model,
        vllm=tuned_vllm,
    )


async def build_vllm_realtime(settings: AppSettings) -> tuple[Any, Any, Any, Any, AppSettings]:
    """Create (engine_stack, engine_client, serving_models, serving_realtime, tuned_settings)."""

    # Ensure a writable local snapshot exists and tekken.json delay is patched.
    settings.model.model_dir.mkdir(parents=True, exist_ok=True)
    model_dir = ensure_voxtral_snapshot(settings.model)

    max_num_seqs = _tune_max_num_seqs(settings, model_dir)
    engine_args = _build_engine_args(settings, model_dir, max_num_seqs=max_num_seqs)

    logger.info("vllm: building engine (model=%s)", model_dir)
    engine_stack = contextlib.AsyncExitStack()
    engine_cm = build_async_engine_client_from_engine_args(
        engine_args,
        usage_context=UsageContext.OPENAI_API_SERVER,
    )
    engine_client = await engine_stack.enter_async_context(engine_cm)

    serving_models = await _build_serving_models(engine_client, settings, model_dir)

    serving_realtime = OpenAIServingRealtime(
        engine_client,
        serving_models,
        request_logger=None,
    )

    tuned_settings = _with_vllm_max_num_seqs(settings, max_num_seqs=max_num_seqs)
    return engine_stack, engine_client, serving_models, serving_realtime, tuned_settings


__all__ = ["build_vllm_realtime"]
