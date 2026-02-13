from __future__ import annotations

import os

from src.handlers.websocket.auth import validate_api_key


def test_validate_api_key_misconfigured() -> None:
    os.environ.pop("VOXTRAL_API_KEY", None)
    assert validate_api_key("anything") is False


def test_validate_api_key_matches() -> None:
    os.environ["VOXTRAL_API_KEY"] = "secret"
    assert validate_api_key("secret") is True
    assert validate_api_key("wrong") is False
