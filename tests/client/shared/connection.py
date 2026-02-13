from __future__ import annotations

import os
from typing import Any

from params import config
from utils.network import ws_url, append_auth_query


def build_url(server: str, secure: bool) -> str:
    url = ws_url(server, secure)
    api_key = (os.getenv(config.ENV_VOXTRAL_API_KEY) or "").strip()
    if not api_key:
        return url
    return append_auth_query(url, api_key, override=True)


def get_ws_options(auth_headers: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    return {
        "additional_headers": auth_headers or [],
        "ping_interval": config.WS_PING_INTERVAL_S,
        "ping_timeout": config.WS_PING_TIMEOUT_S,
        "max_size": config.WS_MAX_MESSAGE_BYTES,
    }


__all__ = ["build_url", "get_ws_options"]
