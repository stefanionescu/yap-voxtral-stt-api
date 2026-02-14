"""Runtime settings (dataclasses only)."""

from __future__ import annotations

from typing import Any
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthSettings:
    api_key: str


@dataclass(frozen=True, slots=True)
class LimitsSettings:
    max_concurrent_connections: int
    ws_message_window_seconds: float
    ws_max_messages_per_window: int
    ws_cancel_window_seconds: float
    ws_max_cancels_per_window: int


@dataclass(frozen=True, slots=True)
class WebSocketSettings:
    idle_timeout_s: float
    watchdog_tick_s: float
    max_connection_duration_s: float
    inbound_queue_max: int


@dataclass(frozen=True, slots=True)
class ModelSettings:
    model_id: str
    served_model_name: str
    transcription_delay_ms: int
    model_dir: Path
    tekken_filename: str


@dataclass(frozen=True, slots=True)
class VllmSettings:
    dtype: str
    gpu_memory_utilization: float
    max_model_len: int
    max_num_seqs: int
    max_num_batched_tokens: int
    enforce_eager: bool
    kv_cache_dtype: str
    calculate_kv_scales: bool
    tokenizer_mode: str
    config_format: str
    load_format: str
    compilation_config: dict[str, Any] | None
    disable_compile_cache: bool


@dataclass(frozen=True, slots=True)
class AppSettings:
    auth: AuthSettings
    limits: LimitsSettings
    websocket: WebSocketSettings
    model: ModelSettings
    vllm: VllmSettings


__all__ = [
    "AppSettings",
    "AuthSettings",
    "LimitsSettings",
    "ModelSettings",
    "VllmSettings",
    "WebSocketSettings",
]
