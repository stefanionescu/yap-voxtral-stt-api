from __future__ import annotations

from collections.abc import Iterator


def iter_pcm16_chunks(pcm_bytes: bytes, *, chunk_bytes: int) -> Iterator[bytes]:
    if chunk_bytes <= 0:
        raise ValueError("chunk_bytes must be > 0")
    for i in range(0, len(pcm_bytes), chunk_bytes):
        yield pcm_bytes[i : i + chunk_bytes]


__all__ = ["iter_pcm16_chunks"]
