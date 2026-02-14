#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/deps.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"

log_section "[deps] Installing dependencies"

# Ensure uv is available (preferred installer for CUDA 13 wheels).
if ! command -v uv >/dev/null 2>&1; then
  log_info "[deps] Installing uv"
  pip install uv 2>&1 | tail -1
fi

if command -v uv >/dev/null 2>&1; then
  log_info "[deps] Using uv pip"
  uv pip install --python "${VENV_DIR}/bin/python" -U pip
  uv pip install --python "${VENV_DIR}/bin/python" -r "${REQ_FILE}" \
    --extra-index-url "${PYTORCH_CUDA_INDEX_URL}" \
    --index-strategy unsafe-best-match \
    --torch-backend=cu130
else
  log_warn "[deps] uv not found; falling back to pip"
  "${VENV_DIR}/bin/python" -m pip install -U pip
  "${VENV_DIR}/bin/python" -m pip install -r "${REQ_FILE}" --extra-index-url "${PYTORCH_CUDA_INDEX_URL}"
fi

# FlashInfer is pre-installed on some cloud images but Voxtral's whisper-causal
# encoder does not support it. vLLM v1 auto-selects FlashInfer when present,
# so remove it to fall back to flash-attn.
if "${VENV_DIR}/bin/python" -c "import flashinfer" 2>/dev/null; then
  log_info "[deps] Removing flashinfer (unsupported by whisper-causal encoder)"
  if command -v uv >/dev/null 2>&1; then
    uv pip uninstall --python "${VENV_DIR}/bin/python" flashinfer flashinfer-python 2>/dev/null || true
  else
    "${VENV_DIR}/bin/pip" uninstall -y flashinfer flashinfer-python 2>/dev/null || true
  fi
fi
