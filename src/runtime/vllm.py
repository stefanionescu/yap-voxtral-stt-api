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
from .gpu_profiles import select_max_num_batched_tokens

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


def _detect_cuda_capability() -> tuple[int, int] | None:
    try:
        import torch  # type: ignore

        if not torch.cuda.is_available():
            return None
        cap = torch.cuda.get_device_capability(0)
        if not isinstance(cap, tuple) or len(cap) != 2:
            return None
        major, minor = cap
        return int(major), int(minor)
    except Exception:
        return None


def _detect_gpu_name() -> str | None:
    # Prefer torch when available (matches the actual device vLLM will run on).
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            if isinstance(name, str) and name.strip():
                return name.strip()
    except Exception:
        pass

    # Fallback: nvidia-smi (works before torch is imported/initialized).
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None

    try:
        proc = subprocess.run(  # noqa: S603
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None
    return lines[0]


def _gpu_supports_fp8() -> bool:
    # vLLM considers FP8-capable CUDA GPUs to be compute capability >= 8.9 (Ada/Hopper+).
    cap = _detect_cuda_capability()
    if cap is None:
        return False
    major, minor = cap
    return (major, minor) >= (8, 9)


def _select_kv_cache_dtype(settings: AppSettings) -> str:
    if _env_is_set("VLLM_KV_CACHE_DTYPE"):
        dt = (settings.vllm.kv_cache_dtype or "").strip()
    else:
        # Voxtral's whisper-causal encoder requires FlashAttentionBackend, which
        # does not support fp8 KV cache in vLLM v1 (only TritonAttentionBackend
        # does). Force "auto" to ensure FlashAttention is selected.
        dt = "auto"

    # Compatibility: some docs/older configs use fp8_e4m3fn; vLLM uses fp8_e4m3.
    dt_l = dt.lower()
    if dt_l == "fp8_e4m3fn":
        return "fp8_e4m3"
    return dt


def _select_calculate_kv_scales(settings: AppSettings, *, kv_cache_dtype: str) -> bool:
    if _env_is_set("VLLM_CALCULATE_KV_SCALES"):
        return bool(settings.vllm.calculate_kv_scales)
    return (kv_cache_dtype or "").strip().lower().startswith("fp8")


def _select_max_num_batched_tokens(settings: AppSettings) -> int:
    # Not env-configurable: we pick a sane per-GPU default to avoid footguns.
    gpu_name = _detect_gpu_name()
    if not gpu_name:
        return int(settings.vllm.max_num_batched_tokens)
    return int(select_max_num_batched_tokens(gpu_name))


def _read_mistral_params(model_dir: Path) -> dict[str, int] | None:
    params_path = model_dir / "params.json"
    if not params_path.exists():
        return None

    doc: Any | None
    try:
        doc = json.loads(params_path.read_text(encoding="utf-8"))
    except Exception:
        doc = None

    if isinstance(doc, dict):
        out: dict[str, int] = {}
        for key, aliases in {
            "dim": ("dim", "hidden_size", "d_model"),
            "n_layers": ("n_layers", "num_hidden_layers", "num_layers"),
            "n_kv_heads": ("n_kv_heads", "num_key_value_heads"),
            "head_dim": ("head_dim", "kv_head_dim"),
            "sliding_window": ("sliding_window",),
        }.items():
            v: Any | None = None
            for a in aliases:
                if a in doc:
                    v = doc.get(a)
                    break
            if v is None:
                continue
            try:
                out[key] = int(v)
            except Exception:
                continue

        # Basic sanity check.
        if out.get("n_layers", 0) <= 0:
            return None
        return out

    return None


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

    arch = _read_mistral_params(model_dir) or {}
    n_layers = int(arch.get("n_layers", 0))
    n_kv_heads = int(arch.get("n_kv_heads", 0))
    head_dim = int(arch.get("head_dim", 0))
    sliding_window = int(arch.get("sliding_window", 0))

    if n_layers <= 0:
        return None

    weights_bytes = _sum_safetensors_bytes(model_dir)

    kv_bytes = _kv_cache_bytes_per_element(
        kv_cache_dtype=settings.vllm.kv_cache_dtype,
        model_dtype=settings.vllm.dtype,
    )

    # vLLM KV planning for sliding-window models uses:
    #   num_tokens = min(sliding_window - 1 + max_num_batched_tokens, max_model_len)
    # When a model exposes GQA params (n_kv_heads/head_dim), KV is sized on those.
    if n_kv_heads > 0 and head_dim > 0:
        per_token_bytes = 2 * n_layers * n_kv_heads * head_dim * kv_bytes
    else:
        dim = int(arch.get("dim", 0))
        if dim <= 0:
            return None
        per_token_bytes = 2 * n_layers * dim * kv_bytes

    max_model_len = int(max(1, settings.vllm.max_model_len))
    max_batched = int(max(1, settings.vllm.max_num_batched_tokens))
    if sliding_window > 0:
        kv_tokens = min(max_model_len, max(1, int(sliding_window) - 1 + max_batched))
    else:
        kv_tokens = max_model_len

    per_seq_bytes = int(per_token_bytes) * int(kv_tokens)
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
        "calculate_kv_scales": settings.vllm.calculate_kv_scales,
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
        calculate_kv_scales=settings.vllm.calculate_kv_scales,
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

    kv_cache_dtype = _select_kv_cache_dtype(settings)
    calculate_kv_scales = _select_calculate_kv_scales(settings, kv_cache_dtype=kv_cache_dtype)
    max_num_batched_tokens = _select_max_num_batched_tokens(settings)
    if (
        kv_cache_dtype != settings.vllm.kv_cache_dtype
        or bool(calculate_kv_scales) != bool(settings.vllm.calculate_kv_scales)
        or int(max_num_batched_tokens) != int(settings.vllm.max_num_batched_tokens)
    ):
        settings = AppSettings(
            auth=settings.auth,
            limits=settings.limits,
            websocket=settings.websocket,
            model=settings.model,
            vllm=VllmSettings(
                dtype=settings.vllm.dtype,
                gpu_memory_utilization=settings.vllm.gpu_memory_utilization,
                max_model_len=settings.vllm.max_model_len,
                max_num_seqs=settings.vllm.max_num_seqs,
                max_num_batched_tokens=int(max_num_batched_tokens),
                enforce_eager=settings.vllm.enforce_eager,
                kv_cache_dtype=kv_cache_dtype,
                calculate_kv_scales=calculate_kv_scales,
                tokenizer_mode=settings.vllm.tokenizer_mode,
                config_format=settings.vllm.config_format,
                load_format=settings.vllm.load_format,
                compilation_config=settings.vllm.compilation_config,
                disable_compile_cache=settings.vllm.disable_compile_cache,
            ),
        )

    # Log the selection for operator visibility (important for tuning).
    try:
        gpu_name = _detect_gpu_name()
    except Exception:
        gpu_name = None
    if gpu_name:
        logger.info(
            "vllm: max_num_batched_tokens=%s (gpu=%s)", int(settings.vllm.max_num_batched_tokens), gpu_name
        )
    else:
        logger.info("vllm: max_num_batched_tokens=%s", int(settings.vllm.max_num_batched_tokens))

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
