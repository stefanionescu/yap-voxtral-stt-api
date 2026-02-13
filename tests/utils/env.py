"""Environment helpers for client scripts.

Helpers for CLI scripts to derive server defaults and apply key overrides.
"""

from __future__ import annotations

import os as _os

DEFAULT_SERVER = "127.0.0.1:8000"


def derive_default_server() -> str:
    """Compute default server endpoint from shell environment or use default.

    Prefers VOXTRAL_SERVER, falling back to localhost:8000.
    """
    return _os.getenv("VOXTRAL_SERVER", DEFAULT_SERVER)


def apply_key_overrides(api_key: str | None) -> None:
    if api_key:
        _os.environ["VOXTRAL_API_KEY"] = api_key


__all__ = ["apply_key_overrides", "derive_default_server"]
