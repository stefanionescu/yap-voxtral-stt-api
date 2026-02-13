from __future__ import annotations

from src.handlers.websocket.auth import validate_api_key


def test_validate_api_key_misconfigured() -> None:
    assert validate_api_key("anything", "") is False


def test_validate_api_key_matches() -> None:
    assert validate_api_key("secret", "secret") is True
    assert validate_api_key("wrong", "secret") is False
