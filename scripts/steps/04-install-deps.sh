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

# ---------------------------------------------------------------------------
# Helper: install a package via uv (preferred) or pip (fallback).
# ---------------------------------------------------------------------------
_pip_install() {
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "${VENV_DIR}/bin/python" "$@"
  else
    "${VENV_DIR}/bin/pip" install "$@"
  fi
}

# Ensure uv is available (preferred installer for CUDA wheels).
if ! command -v uv >/dev/null 2>&1; then
  log_info "[deps] Installing uv"
  pip install uv
fi

# ---------------------------------------------------------------------------
# Pre-install vLLM from the GitHub release wheel (not on PyPI).
# ---------------------------------------------------------------------------
log_info "[deps] Installing vLLM from wheel"
_pip_install "${VLLM_WHEEL_URL}"

# ---------------------------------------------------------------------------
# Main requirements (PyTorch + app deps).
# ---------------------------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
  log_info "[deps] Using uv pip"
  uv pip install --python "${VENV_DIR}/bin/python" -U pip
  uv pip install --python "${VENV_DIR}/bin/python" -r "${REQ_FILE}" \
    --extra-index-url "${PYTORCH_CUDA_INDEX_URL}" \
    --index-strategy unsafe-best-match \
    --torch-backend="${TORCH_BACKEND}"
else
  log_warn "[deps] uv not found; falling back to pip"
  "${VENV_DIR}/bin/python" -m pip install -U pip
  "${VENV_DIR}/bin/python" -m pip install -r "${REQ_FILE}" --extra-index-url "${PYTORCH_CUDA_INDEX_URL}"
fi

# FlashInfer is pre-installed on some cloud images but Voxtral's whisper-causal
# encoder only supports FlashAttentionBackend. vLLM v1 auto-selects FlashInfer
# when present, so remove it to let flash-attn be chosen instead.
if "${VENV_DIR}/bin/python" -c "import flashinfer" 2>/dev/null; then
  log_info "[deps] Removing flashinfer (unsupported by whisper-causal encoder)"
  if command -v uv >/dev/null 2>&1; then
    uv pip uninstall --python "${VENV_DIR}/bin/python" flashinfer flashinfer-python 2>/dev/null || true
  else
    "${VENV_DIR}/bin/pip" uninstall -y flashinfer flashinfer-python 2>/dev/null || true
  fi
fi

# ---------------------------------------------------------------------------
# flash-attn: try a prebuilt wheel first, fall back to source build.
# ---------------------------------------------------------------------------
if ! "${VENV_DIR}/bin/python" -c "import flash_attn" 2>/dev/null; then
  log_info "[deps] Installing flash-attn ${FLASH_ATTN_VERSION} (required by whisper-causal encoder)"

  # Detect runtime values needed to construct the prebuilt wheel filename.
  TORCH_VER="$("${VENV_DIR}/bin/python" -c "import torch; v=torch.__version__.split('+')[0].split('.')[:2]; print('.'.join(v))")"
  CXX11_ABI="$("${VENV_DIR}/bin/python" -c "import torch; print(int(torch._C._GLIBCXX_USE_CXX11_ABI))" 2>/dev/null || echo "TRUE")"
  PY_TAG="cp$("${VENV_DIR}/bin/python" -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")"

  WHEEL_NAME="flash_attn-${FLASH_ATTN_VERSION}+cu12torch${TORCH_VER}cxx11abi${CXX11_ABI}-${PY_TAG}-${PY_TAG}-linux_x86_64.whl"
  WHEEL_URL="https://github.com/Dao-AILab/flash-attention/releases/download/v${FLASH_ATTN_VERSION}/${WHEEL_NAME}"

  log_info "[deps] Trying prebuilt wheel: ${WHEEL_NAME}"
  if _pip_install "${WHEEL_URL}" 2>/dev/null; then
    log_info "[deps] flash-attn installed from prebuilt wheel"
  else
    log_info "[deps] Prebuilt wheel not available; building flash-attn from source"
    _pip_install wheel ninja psutil
    MAX_JOBS="${MAX_JOBS:-$(nproc 2>/dev/null || echo 4)}" _pip_install "flash-attn==${FLASH_ATTN_VERSION}" --no-build-isolation
  fi
fi
