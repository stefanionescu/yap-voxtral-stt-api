"""Model snapshot + Voxtral-specific patching helpers."""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path

from src.state.settings import ModelSettings

logger = logging.getLogger(__name__)

DELAY_MIN_MS = 80
DELAY_MAX_MS = 2400
DELAY_STEP_MS = 80


def _validate_delay_ms(delay_ms: int) -> int:
    if delay_ms < DELAY_MIN_MS or delay_ms > DELAY_MAX_MS or (delay_ms % DELAY_STEP_MS) != 0:
        raise ValueError(
            f"VOXTRAL_TRANSCRIPTION_DELAY_MS must be a multiple of {DELAY_STEP_MS} between {DELAY_MIN_MS} and"
            f" {DELAY_MAX_MS}"
        )
    return delay_ms


def _patch_tekken_json(model_dir: Path, *, tekken_filename: str, delay_ms: int) -> bool:
    tekken_path = model_dir / tekken_filename
    if not tekken_path.exists():
        logger.warning("voxtral: tekken file not found at %s (skipping delay patch)", tekken_path)
        return False

    doc = json.loads(tekken_path.read_text(encoding="utf-8"))
    current = doc.get("transcription_delay_ms")
    if current == delay_ms:
        return False

    doc["transcription_delay_ms"] = delay_ms
    tekken_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info("voxtral: patched %s transcription_delay_ms=%s", tekken_path, delay_ms)
    return True


def _looks_like_snapshot(model_dir: Path, *, tekken_filename: str) -> bool:
    # Voxtral repos don't necessarily ship a transformers-style config.json.
    if not (model_dir / "params.json").exists():
        return False
    if not (model_dir / tekken_filename).exists():
        return False
    return any(model_dir.glob("*.safetensors"))


def ensure_voxtral_snapshot(model: ModelSettings) -> Path:
    """Ensure we have a writable local model directory and tekken delay patch applied."""
    delay_ms = _validate_delay_ms(int(model.transcription_delay_ms))

    model_dir = model.model_dir
    model_dir.mkdir(parents=True, exist_ok=True)

    if not _looks_like_snapshot(model_dir, tekken_filename=model.tekken_filename):
        token = (os.getenv("HF_TOKEN") or "").strip() or None

        # Local snapshot avoids mutating the HF cache and lets us patch tekken.json safely.
        from huggingface_hub import snapshot_download  # noqa: PLC0415

        logger.info("voxtral: downloading snapshot repo_id=%s -> %s", model.model_id, model_dir)
        snapshot_download(
            repo_id=model.model_id,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
            token=token,
        )

    _patch_tekken_json(model_dir, tekken_filename=model.tekken_filename, delay_ms=delay_ms)
    return model_dir


__all__ = ["ensure_voxtral_snapshot"]
