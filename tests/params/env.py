"""Environment helpers for client scripts.

Helpers for CLI scripts to derive server defaults and apply key overrides.
"""

from __future__ import annotations

import os as _os

DEFAULT_SERVER = "127.0.0.1:8000"


def derive_default_server() -> str:
    """Compute default server endpoint from shell environment or use default.

    Prefers CLOUD_TCP_HOST/CLOUD_HOST/CLOUD_SERVER and CLOUD_TCP_PORT/CLOUD_PORT,
    falling back to VOXTRAL_SERVER then localhost:8000.
    """
    cloud_host = _os.getenv("CLOUD_TCP_HOST") or _os.getenv("CLOUD_HOST") or _os.getenv("CLOUD_SERVER")
    cloud_port = _os.getenv("CLOUD_TCP_PORT") or _os.getenv("CLOUD_PORT") or "8000"
    if cloud_host:
        return f"{cloud_host}:{cloud_port}"
    return _os.getenv("VOXTRAL_SERVER", DEFAULT_SERVER)


def apply_key_overrides(api_key: str | None) -> None:
    if api_key:
        _os.environ["VOXTRAL_API_KEY"] = api_key


__all__ = ["apply_key_overrides", "derive_default_server"]
