from __future__ import annotations

import os


def derive_default_server() -> str:
    return (os.getenv("VOXTRAL_SERVER") or "localhost:8000").strip()


def resolve_api_key(override: str | None = None) -> str | None:
    if override:
        return override
    key = (os.getenv("VOXTRAL_API_KEY") or "").strip()
    return key or None


def build_ws_url(server: str, *, secure: bool, api_key: str) -> str:
    s = server.strip()
    if s.startswith("ws://") or s.startswith("wss://"):
        base = s
    else:
        scheme = "wss" if secure else "ws"
        base = f"{scheme}://{s}"
    if base.endswith("/"):
        base = base[:-1]
    return f"{base}/ws?api_key={api_key}"


__all__ = ["build_ws_url", "derive_default_server", "resolve_api_key"]
