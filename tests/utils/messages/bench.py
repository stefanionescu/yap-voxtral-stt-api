from __future__ import annotations

from .streaming import MessageHandler


class BenchMessageHandler(MessageHandler):
    """Bench-specific handler that tags capacity rejection."""

    def handle_error(self, payload: dict) -> None:
        code = (payload.get("code") or "").strip().lower()
        if code == "server_at_capacity":
            self.reject_reason = "capacity"
        super().handle_error(payload)


__all__ = ["BenchMessageHandler"]
