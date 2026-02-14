"""Load runtime settings.

Configuration values are resolved from the environment in `src/config/*` and
exposed here as structured dataclasses for the rest of the server.
"""

from __future__ import annotations

from src.config.secrets import VOXTRAL_API_KEY
from src.config.websocket import (
    WS_IDLE_TIMEOUT_S,
    WS_WATCHDOG_TICK_S,
    WS_INBOUND_QUEUE_MAX,
    WS_MAX_CONNECTION_DURATION_S,
)
from src.state.settings import (
    AppSettings,
    AuthSettings,
    VllmSettings,
    ModelSettings,
    LimitsSettings,
    WebSocketSettings,
)
from src.config.models import (
    VOXTRAL_MODEL_ID,
    VOXTRAL_MODEL_DIR,
    VOXTRAL_TEKKEN_FILENAME,
    VOXTRAL_SERVED_MODEL_NAME,
    VOXTRAL_TRANSCRIPTION_DELAY_MS,
)
from src.config.limits import (
    MAX_CONCURRENT_CONNECTIONS,
)
from src.config.vllm import (
    VLLM_DTYPE,
    VLLM_LOAD_FORMAT,
    VLLM_MAX_NUM_SEQS,
    VLLM_CONFIG_FORMAT,
    VLLM_ENFORCE_EAGER,
    VLLM_MAX_MODEL_LEN,
    VLLM_KV_CACHE_DTYPE,
    VLLM_CALCULATE_KV_SCALES,
    VLLM_TOKENIZER_MODE,
    VLLM_COMPILATION_CONFIG,
    VLLM_DISABLE_COMPILE_CACHE,
    VLLM_GPU_MEMORY_UTILIZATION,
    VLLM_MAX_NUM_BATCHED_TOKENS,
)


def load_settings() -> AppSettings:
    return AppSettings(
        auth=AuthSettings(api_key=VOXTRAL_API_KEY),
        limits=LimitsSettings(
            max_concurrent_connections=MAX_CONCURRENT_CONNECTIONS,
        ),
        websocket=WebSocketSettings(
            idle_timeout_s=WS_IDLE_TIMEOUT_S,
            watchdog_tick_s=WS_WATCHDOG_TICK_S,
            max_connection_duration_s=WS_MAX_CONNECTION_DURATION_S,
            inbound_queue_max=WS_INBOUND_QUEUE_MAX,
        ),
        model=ModelSettings(
            model_id=VOXTRAL_MODEL_ID,
            served_model_name=VOXTRAL_SERVED_MODEL_NAME,
            transcription_delay_ms=VOXTRAL_TRANSCRIPTION_DELAY_MS,
            model_dir=VOXTRAL_MODEL_DIR,
            tekken_filename=VOXTRAL_TEKKEN_FILENAME,
        ),
        vllm=VllmSettings(
            dtype=VLLM_DTYPE,
            gpu_memory_utilization=VLLM_GPU_MEMORY_UTILIZATION,
            max_model_len=VLLM_MAX_MODEL_LEN,
            max_num_seqs=VLLM_MAX_NUM_SEQS,
            max_num_batched_tokens=VLLM_MAX_NUM_BATCHED_TOKENS,
            enforce_eager=VLLM_ENFORCE_EAGER,
            kv_cache_dtype=VLLM_KV_CACHE_DTYPE,
            calculate_kv_scales=VLLM_CALCULATE_KV_SCALES,
            tokenizer_mode=VLLM_TOKENIZER_MODE,
            config_format=VLLM_CONFIG_FORMAT,
            load_format=VLLM_LOAD_FORMAT,
            compilation_config=VLLM_COMPILATION_CONFIG,
            disable_compile_cache=VLLM_DISABLE_COMPILE_CACHE,
        ),
    )


__all__ = ["load_settings"]
