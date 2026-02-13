"""vLLM engine configuration (env-driven)."""

from __future__ import annotations

import os
import json
from typing import Any


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


VLLM_DTYPE = os.getenv("VLLM_DTYPE", "bfloat16").strip()
VLLM_GPU_MEMORY_UTILIZATION = _float_env("VLLM_GPU_MEMORY_UTILIZATION", 0.92)

# Voxtral Realtime is ~12.5 "steps"/sec (~80ms/token). Default max connection duration is 90 minutes:
# 90min = 5400s; 5400 / 0.08 = 67500 tokens.
VLLM_MAX_MODEL_LEN = _int_env("VLLM_MAX_MODEL_LEN", 67500)
VLLM_MAX_NUM_SEQS = _int_env("VLLM_MAX_NUM_SEQS", 128)
VLLM_MAX_NUM_BATCHED_TOKENS = _int_env("VLLM_MAX_NUM_BATCHED_TOKENS", 4096)

VLLM_ENFORCE_EAGER = _bool_env("VLLM_ENFORCE_EAGER", False)

# KV cache dtype: "auto", "fp8_e4m3fn", "fp8_e5m2", etc. (vLLM-dependent).
VLLM_KV_CACHE_DTYPE = os.getenv("VLLM_KV_CACHE_DTYPE", "auto").strip()

# Voxtral recommends Mistral-specific loading flags for vLLM:
#   --tokenizer-mode mistral --config-format mistral --load-format mistral
VLLM_TOKENIZER_MODE = os.getenv("VLLM_TOKENIZER_MODE", "mistral").strip()
VLLM_CONFIG_FORMAT = os.getenv("VLLM_CONFIG_FORMAT", "mistral").strip()
VLLM_LOAD_FORMAT = os.getenv("VLLM_LOAD_FORMAT", "mistral").strip()

# Optional JSON string for vLLM compilation config.
_comp_raw = os.getenv("VLLM_COMPILATION_CONFIG", "").strip()
VLLM_COMPILATION_CONFIG: dict[str, Any] | None = None
if _comp_raw:
    try:
        VLLM_COMPILATION_CONFIG = json.loads(_comp_raw)
    except Exception:
        VLLM_COMPILATION_CONFIG = None

# If set, we pass disable_compile_cache to engine args when supported.
VLLM_DISABLE_COMPILE_CACHE = _bool_env("VLLM_DISABLE_COMPILE_CACHE", True)

__all__ = [
    "VLLM_DTYPE",
    "VLLM_GPU_MEMORY_UTILIZATION",
    "VLLM_MAX_MODEL_LEN",
    "VLLM_MAX_NUM_SEQS",
    "VLLM_MAX_NUM_BATCHED_TOKENS",
    "VLLM_ENFORCE_EAGER",
    "VLLM_KV_CACHE_DTYPE",
    "VLLM_TOKENIZER_MODE",
    "VLLM_CONFIG_FORMAT",
    "VLLM_LOAD_FORMAT",
    "VLLM_COMPILATION_CONFIG",
    "VLLM_DISABLE_COMPILE_CACHE",
]
