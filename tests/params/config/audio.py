from __future__ import annotations

# Voxtral Realtime via vLLM expects PCM16 mono at 16kHz.
ASR_SAMPLE_RATE: int = 16000

# Stream chunk size (ms). 80ms aligns with Voxtral's 12.5Hz step.
CHUNK_MS: int = 80
CHUNK_SAMPLES: int = int(ASR_SAMPLE_RATE * (CHUNK_MS / 1000.0))

FFMPEG_DECODE_SR_16K: int = 16000

SAMPLES_DIR_NAME: str = "samples"
FILE_EXTS = {".wav", ".flac", ".ogg", ".mp3"}
