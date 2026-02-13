"""vLLM engine configuration (env-resolved constants only)."""

from __future__ import annotations

import os
import json
from typing import Any

VLLM_DTYPE: str = (os.getenv("VLLM_DTYPE") or "").strip() or "bfloat16"

_GPU_UTIL_RAW = (os.getenv("VLLM_GPU_MEMORY_UTILIZATION") or "").strip()
try:
    VLLM_GPU_MEMORY_UTILIZATION: float = float(_GPU_UTIL_RAW) if _GPU_UTIL_RAW else 0.92
except Exception:
    VLLM_GPU_MEMORY_UTILIZATION = 0.92
if VLLM_GPU_MEMORY_UTILIZATION <= 0.0 or VLLM_GPU_MEMORY_UTILIZATION > 1.0:
    VLLM_GPU_MEMORY_UTILIZATION = 0.92

# Voxtral Realtime is ~12.5 "steps"/sec (~80ms/token).
#
# Default max model length targets a single long utterance of ~5 minutes:
# 5min = 300s; 300 / 0.08 = 3750 steps; use a small buffer -> 4096.
_MAX_MODEL_LEN_RAW = (os.getenv("VLLM_MAX_MODEL_LEN") or "").strip()
try:
    VLLM_MAX_MODEL_LEN: int = int(_MAX_MODEL_LEN_RAW) if _MAX_MODEL_LEN_RAW else 4096
except Exception:
    VLLM_MAX_MODEL_LEN = 4096
VLLM_MAX_MODEL_LEN = max(1, int(VLLM_MAX_MODEL_LEN))

_MAX_NUM_SEQS_RAW = (os.getenv("VLLM_MAX_NUM_SEQS") or "").strip()
try:
    VLLM_MAX_NUM_SEQS: int = int(_MAX_NUM_SEQS_RAW) if _MAX_NUM_SEQS_RAW else 128
except Exception:
    VLLM_MAX_NUM_SEQS = 128
VLLM_MAX_NUM_SEQS = max(1, int(VLLM_MAX_NUM_SEQS))

_MAX_BATCHED_TOKENS_RAW = (os.getenv("VLLM_MAX_NUM_BATCHED_TOKENS") or "").strip()
try:
    VLLM_MAX_NUM_BATCHED_TOKENS: int = int(_MAX_BATCHED_TOKENS_RAW) if _MAX_BATCHED_TOKENS_RAW else 4096
except Exception:
    VLLM_MAX_NUM_BATCHED_TOKENS = 4096
VLLM_MAX_NUM_BATCHED_TOKENS = max(1, int(VLLM_MAX_NUM_BATCHED_TOKENS))

_ENFORCE_EAGER_RAW = (os.getenv("VLLM_ENFORCE_EAGER") or "").strip().lower()
VLLM_ENFORCE_EAGER: bool = _ENFORCE_EAGER_RAW in {"1", "true", "yes", "y", "on"} if _ENFORCE_EAGER_RAW else False

# KV cache dtype: "auto", "fp8_e4m3fn", "fp8_e5m2", etc. (vLLM-dependent).
VLLM_KV_CACHE_DTYPE: str = (os.getenv("VLLM_KV_CACHE_DTYPE") or "").strip() or "auto"

# Voxtral recommends Mistral-specific loading flags for vLLM:
#   --tokenizer-mode mistral --config-format mistral --load-format mistral
VLLM_TOKENIZER_MODE: str = (os.getenv("VLLM_TOKENIZER_MODE") or "").strip() or "mistral"

VLLM_CONFIG_FORMAT: str = (os.getenv("VLLM_CONFIG_FORMAT") or "").strip() or "mistral"

VLLM_LOAD_FORMAT: str = (os.getenv("VLLM_LOAD_FORMAT") or "").strip() or "mistral"

# Optional JSON string for vLLM compilation config.
#
# Voxtral realtime may require disabling full CUDA graphs in vLLM. Keep the default conservative.
_COMPILATION_RAW = (os.getenv("VLLM_COMPILATION_CONFIG") or "").strip()
if not _COMPILATION_RAW:
    VLLM_COMPILATION_CONFIG: dict[str, Any] | None = {"cudagraph_mode": "PIECEWISE"}
elif _COMPILATION_RAW.lower() in {"none", "null"}:
    VLLM_COMPILATION_CONFIG = None
else:
    try:
        _parsed = json.loads(_COMPILATION_RAW)
    except Exception:
        _parsed = {"cudagraph_mode": "PIECEWISE"}
    if _parsed is None:
        VLLM_COMPILATION_CONFIG = None
    elif isinstance(_parsed, dict):
        VLLM_COMPILATION_CONFIG = _parsed
    else:
        VLLM_COMPILATION_CONFIG = {"cudagraph_mode": "PIECEWISE"}

_DISABLE_COMPILE_CACHE_RAW = (os.getenv("VLLM_DISABLE_COMPILE_CACHE") or "").strip().lower()
VLLM_DISABLE_COMPILE_CACHE: bool = (
    _DISABLE_COMPILE_CACHE_RAW in {"1", "true", "yes", "y", "on"} if _DISABLE_COMPILE_CACHE_RAW else True
)

__all__ = [
    "VLLM_COMPILATION_CONFIG",
    "VLLM_CONFIG_FORMAT",
    "VLLM_DISABLE_COMPILE_CACHE",
    "VLLM_DTYPE",
    "VLLM_ENFORCE_EAGER",
    "VLLM_GPU_MEMORY_UTILIZATION",
    "VLLM_KV_CACHE_DTYPE",
    "VLLM_LOAD_FORMAT",
    "VLLM_MAX_MODEL_LEN",
    "VLLM_MAX_NUM_BATCHED_TOKENS",
    "VLLM_MAX_NUM_SEQS",
    "VLLM_TOKENIZER_MODE",
]
