"""File and audio processing utilities for test clients."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess  # noqa: S404

import numpy as np

try:
    import soundfile as sf  # Optional; we fall back to ffmpeg if unavailable
except Exception:  # pragma: no cover
    sf = None

from tests.params import config

SAMPLES_DIR = Path(config.SAMPLES_DIR_NAME)
EXTS = config.FILE_EXTS


def find_sample_files() -> list[str]:
    if not SAMPLES_DIR.exists():
        return []
    files: list[str] = []
    for root, _, filenames in os.walk(SAMPLES_DIR):
        for f in filenames:
            if Path(f).suffix.lower() in EXTS:
                files.append(str(Path(root) / f))
    return files


def find_sample_by_name(filename: str) -> str | None:
    target = SAMPLES_DIR / filename
    if target.exists() and target.suffix.lower() in EXTS:
        return str(target)
    return None


def _ffmpeg_decode_to_pcm16_mono_16k(path: str) -> tuple[np.ndarray, int]:
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        path,
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(config.FFMPEG_DECODE_SR_16K),
        "pipe:1",
    ]
    p = subprocess.run(  # noqa: S603
        cmd,
        check=True,
        capture_output=True,
    )
    pcm = np.frombuffer(p.stdout, dtype=np.int16)
    return pcm, config.FFMPEG_DECODE_SR_16K


def file_to_pcm16_mono_16k(path: str) -> bytes:
    """Load arbitrary audio file and return PCM16 mono @16k bytes."""
    if sf is not None:
        try:
            x, sr = sf.read(path, dtype="int16", always_2d=False)
            if getattr(x, "ndim", 1) > 1:
                x = x[:, 0]
            if sr != config.FFMPEG_DECODE_SR_16K:
                pcm, _ = _ffmpeg_decode_to_pcm16_mono_16k(path)
                return pcm.tobytes()
            return x.tobytes()
        except Exception:
            pcm, _ = _ffmpeg_decode_to_pcm16_mono_16k(path)
            return pcm.tobytes()
    pcm, _ = _ffmpeg_decode_to_pcm16_mono_16k(path)
    return pcm.tobytes()


def file_duration_seconds(path: str) -> float:
    if sf is not None:
        try:
            f = sf.SoundFile(path)
            return float(len(f) / f.samplerate)
        except Exception:
            pcm, sr = _ffmpeg_decode_to_pcm16_mono_16k(path)
            return float(len(pcm) / sr)
    pcm, sr = _ffmpeg_decode_to_pcm16_mono_16k(path)
    return float(len(pcm) / sr)


def make_silence_pcm16(seconds: float, *, sr: int = config.ASR_SAMPLE_RATE) -> bytes:
    n = int(max(0.0, seconds) * sr)
    return (np.zeros(n, dtype=np.int16)).tobytes()


__all__ = [
    "SAMPLES_DIR",
    "file_duration_seconds",
    "file_to_pcm16_mono_16k",
    "find_sample_by_name",
    "find_sample_files",
    "make_silence_pcm16",
]
