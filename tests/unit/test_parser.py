from __future__ import annotations

import json

import pytest

from src.handlers.websocket.parser import parse_client_message


def test_parse_client_message_ok() -> None:
    raw = json.dumps({
        "type": "ping",
        "session_id": "s1",
        "request_id": "r1",
        "payload": {"x": 1},
    })
    msg = parse_client_message(raw)
    assert msg["type"] == "ping"
    assert msg["session_id"] == "s1"
    assert msg["request_id"] == "r1"
    assert msg["payload"]["x"] == 1


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        json.dumps([]),
        json.dumps({"session_id": "s", "request_id": "r", "payload": {}}),
        json.dumps({"type": "ping", "request_id": "r", "payload": {}}),
        json.dumps({"type": "ping", "session_id": "s", "payload": {}}),
        json.dumps({"type": "ping", "session_id": "s", "request_id": "r", "payload": []}),
    ],
)
def test_parse_client_message_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_client_message(raw)
