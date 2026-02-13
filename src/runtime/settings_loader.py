"""Environment parsing for runtime settings."""

from __future__ import annotations

import os
import json
from typing import Any
from pathlib import Path

from src.config.secrets import ENV_VOXTRAL_API_KEY
from src.state.settings import (
    AppSettings,
    AuthSettings,
    VllmSettings,
    ModelSettings,
    LimitsSettings,
    WebSocketSettings,
)
from src.config.websocket import (
    ENV_WS_IDLE_TIMEOUT_S,
    ENV_WS_WATCHDOG_TICK_S,
    ENV_WS_INBOUND_QUEUE_MAX,
    DEFAULT_WS_IDLE_TIMEOUT_S,
    DEFAULT_WS_WATCHDOG_TICK_S,
    DEFAULT_WS_INBOUND_QUEUE_MAX,
    ENV_WS_MAX_CONNECTION_DURATION_S,
    DEFAULT_WS_MAX_CONNECTION_DURATION_S,
)
from src.config.models import (
    ENV_VOXTRAL_MODEL_ID,
    ENV_VOXTRAL_MODEL_DIR,
    DEFAULT_VOXTRAL_MODEL_ID,
    DEFAULT_VOXTRAL_MODEL_DIR,
    ENV_VOXTRAL_TEKKEN_FILENAME,
    ENV_VOXTRAL_SERVED_MODEL_NAME,
    DEFAULT_VOXTRAL_TEKKEN_FILENAME,
    ENV_VOXTRAL_TRANSCRIPTION_DELAY_MS,
    DEFAULT_VOXTRAL_TRANSCRIPTION_DELAY_MS,
)
from src.config.limits import (
    ENV_WS_CANCEL_WINDOW_SECONDS,
    ENV_WS_MAX_CANCELS_PER_WINDOW,
    ENV_WS_MESSAGE_WINDOW_SECONDS,
    ENV_MAX_CONCURRENT_CONNECTIONS,
    ENV_WS_MAX_MESSAGES_PER_WINDOW,
    DEFAULT_WS_CANCEL_WINDOW_SECONDS,
    DEFAULT_WS_MAX_CANCELS_PER_WINDOW,
    DEFAULT_WS_MESSAGE_WINDOW_SECONDS,
    DEFAULT_MAX_CONCURRENT_CONNECTIONS,
    DEFAULT_WS_MAX_MESSAGES_PER_WINDOW,
)
from src.config.vllm import (
    ENV_VLLM_DTYPE,
    DEFAULT_VLLM_DTYPE,
    ENV_VLLM_LOAD_FORMAT,
    ENV_VLLM_MAX_NUM_SEQS,
    ENV_VLLM_CONFIG_FORMAT,
    ENV_VLLM_ENFORCE_EAGER,
    ENV_VLLM_MAX_MODEL_LEN,
    ENV_VLLM_KV_CACHE_DTYPE,
    ENV_VLLM_TOKENIZER_MODE,
    DEFAULT_VLLM_LOAD_FORMAT,
    DEFAULT_VLLM_MAX_NUM_SEQS,
    DEFAULT_VLLM_CONFIG_FORMAT,
    DEFAULT_VLLM_ENFORCE_EAGER,
    DEFAULT_VLLM_MAX_MODEL_LEN,
    DEFAULT_VLLM_KV_CACHE_DTYPE,
    DEFAULT_VLLM_TOKENIZER_MODE,
    ENV_VLLM_COMPILATION_CONFIG,
    ENV_VLLM_DISABLE_COMPILE_CACHE,
    DEFAULT_VLLM_COMPILATION_CONFIG,
    ENV_VLLM_GPU_MEMORY_UTILIZATION,
    ENV_VLLM_MAX_NUM_BATCHED_TOKENS,
    DEFAULT_VLLM_DISABLE_COMPILE_CACHE,
    DEFAULT_VLLM_GPU_MEMORY_UTILIZATION,
    DEFAULT_VLLM_MAX_NUM_BATCHED_TOKENS,
)

DELAY_MIN_MS = 80
DELAY_MAX_MS = 2400
DELAY_STEP_MS = 80


def _str_env(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    v = raw.strip()
    return v if v else default


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


def _json_env(name: str, default: dict[str, Any] | None) -> dict[str, Any] | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    v = raw.strip()
    if v.lower() in {"none", "null"}:
        return None
    try:
        parsed = json.loads(v)
    except Exception:
        return default
    if parsed is None:
        return None
    if isinstance(parsed, dict):
        return parsed
    return default


def _validate_delay_ms(delay_ms: int) -> int:
    if delay_ms < DELAY_MIN_MS or delay_ms > DELAY_MAX_MS or (delay_ms % DELAY_STEP_MS) != 0:
        raise ValueError(
            f"{ENV_VOXTRAL_TRANSCRIPTION_DELAY_MS} must be a multiple of {DELAY_STEP_MS} between {DELAY_MIN_MS} and"
            f" {DELAY_MAX_MS}"
        )
    return delay_ms


def _load_auth_settings() -> AuthSettings:
    api_key = (os.getenv(ENV_VOXTRAL_API_KEY) or "").strip()
    return AuthSettings(api_key=api_key)


def _load_model_settings() -> ModelSettings:
    model_id = _str_env(ENV_VOXTRAL_MODEL_ID, DEFAULT_VOXTRAL_MODEL_ID)
    served_model_name = _str_env(ENV_VOXTRAL_SERVED_MODEL_NAME, model_id)

    delay_ms = _validate_delay_ms(_int_env(ENV_VOXTRAL_TRANSCRIPTION_DELAY_MS, DEFAULT_VOXTRAL_TRANSCRIPTION_DELAY_MS))

    model_dir_raw = os.getenv(ENV_VOXTRAL_MODEL_DIR)
    model_dir = (
        Path(model_dir_raw).expanduser() if model_dir_raw and model_dir_raw.strip() else DEFAULT_VOXTRAL_MODEL_DIR
    )

    tekken_filename = _str_env(ENV_VOXTRAL_TEKKEN_FILENAME, DEFAULT_VOXTRAL_TEKKEN_FILENAME)

    return ModelSettings(
        model_id=model_id,
        served_model_name=served_model_name,
        transcription_delay_ms=delay_ms,
        model_dir=model_dir,
        tekken_filename=tekken_filename,
    )


def _load_limits_settings() -> LimitsSettings:
    max_connections = _int_env(ENV_MAX_CONCURRENT_CONNECTIONS, DEFAULT_MAX_CONCURRENT_CONNECTIONS)
    msg_window = _float_env(ENV_WS_MESSAGE_WINDOW_SECONDS, DEFAULT_WS_MESSAGE_WINDOW_SECONDS)
    msg_limit = _int_env(ENV_WS_MAX_MESSAGES_PER_WINDOW, DEFAULT_WS_MAX_MESSAGES_PER_WINDOW)
    cancel_window = _float_env(ENV_WS_CANCEL_WINDOW_SECONDS, DEFAULT_WS_CANCEL_WINDOW_SECONDS)
    if cancel_window <= 0:
        cancel_window = msg_window
    cancel_limit = _int_env(ENV_WS_MAX_CANCELS_PER_WINDOW, DEFAULT_WS_MAX_CANCELS_PER_WINDOW)

    return LimitsSettings(
        max_concurrent_connections=max_connections,
        ws_message_window_seconds=msg_window,
        ws_max_messages_per_window=msg_limit,
        ws_cancel_window_seconds=cancel_window,
        ws_max_cancels_per_window=cancel_limit,
    )


def _load_websocket_settings() -> WebSocketSettings:
    idle_timeout = _float_env(ENV_WS_IDLE_TIMEOUT_S, DEFAULT_WS_IDLE_TIMEOUT_S)
    watchdog_tick = _float_env(ENV_WS_WATCHDOG_TICK_S, DEFAULT_WS_WATCHDOG_TICK_S)
    max_duration = _float_env(ENV_WS_MAX_CONNECTION_DURATION_S, DEFAULT_WS_MAX_CONNECTION_DURATION_S)
    inbound_queue_max = _int_env(ENV_WS_INBOUND_QUEUE_MAX, DEFAULT_WS_INBOUND_QUEUE_MAX)

    return WebSocketSettings(
        idle_timeout_s=idle_timeout,
        watchdog_tick_s=watchdog_tick,
        max_connection_duration_s=max_duration,
        inbound_queue_max=inbound_queue_max,
    )


def _load_vllm_settings() -> VllmSettings:
    return VllmSettings(
        dtype=_str_env(ENV_VLLM_DTYPE, DEFAULT_VLLM_DTYPE),
        gpu_memory_utilization=_float_env(ENV_VLLM_GPU_MEMORY_UTILIZATION, DEFAULT_VLLM_GPU_MEMORY_UTILIZATION),
        max_model_len=_int_env(ENV_VLLM_MAX_MODEL_LEN, DEFAULT_VLLM_MAX_MODEL_LEN),
        max_num_seqs=_int_env(ENV_VLLM_MAX_NUM_SEQS, DEFAULT_VLLM_MAX_NUM_SEQS),
        max_num_batched_tokens=_int_env(ENV_VLLM_MAX_NUM_BATCHED_TOKENS, DEFAULT_VLLM_MAX_NUM_BATCHED_TOKENS),
        enforce_eager=_bool_env(ENV_VLLM_ENFORCE_EAGER, DEFAULT_VLLM_ENFORCE_EAGER),
        kv_cache_dtype=_str_env(ENV_VLLM_KV_CACHE_DTYPE, DEFAULT_VLLM_KV_CACHE_DTYPE),
        tokenizer_mode=_str_env(ENV_VLLM_TOKENIZER_MODE, DEFAULT_VLLM_TOKENIZER_MODE),
        config_format=_str_env(ENV_VLLM_CONFIG_FORMAT, DEFAULT_VLLM_CONFIG_FORMAT),
        load_format=_str_env(ENV_VLLM_LOAD_FORMAT, DEFAULT_VLLM_LOAD_FORMAT),
        compilation_config=_json_env(ENV_VLLM_COMPILATION_CONFIG, DEFAULT_VLLM_COMPILATION_CONFIG),
        disable_compile_cache=_bool_env(ENV_VLLM_DISABLE_COMPILE_CACHE, DEFAULT_VLLM_DISABLE_COMPILE_CACHE),
    )


def load_settings() -> AppSettings:
    return AppSettings(
        auth=_load_auth_settings(),
        limits=_load_limits_settings(),
        websocket=_load_websocket_settings(),
        model=_load_model_settings(),
        vllm=_load_vllm_settings(),
    )


__all__ = ["load_settings"]
