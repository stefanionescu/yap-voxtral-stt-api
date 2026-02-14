#!/usr/bin/env bash
# Detect installed CUDA toolkit version from nvidia-smi.
# Sets: TORCH_BACKEND, PYTORCH_CUDA_INDEX_URL

detect_cuda() {
  # Allow full override — if both are already set, skip detection.
  if [[ -n ${TORCH_BACKEND:-} ]] && [[ -n ${PYTORCH_CUDA_INDEX_URL:-} ]]; then
    return
  fi

  local cuda_version=""
  if command -v nvidia-smi >/dev/null 2>&1; then
    cuda_version="$(nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \K[0-9]+\.[0-9]+' | head -1)"
  fi

  if [[ -z ${cuda_version} ]]; then
    # Fallback: check nvcc
    if command -v nvcc >/dev/null 2>&1; then
      cuda_version="$(nvcc --version 2>/dev/null | grep -oP 'release \K[0-9]+\.[0-9]+' | head -1)"
    fi
  fi

  local major minor
  major="${cuda_version%%.*}"
  minor="${cuda_version#*.}"

  # Map to PyTorch wheel tag.
  case "${major}.${minor}" in
    12.6*) TORCH_BACKEND="${TORCH_BACKEND:-cu126}" ;;
    12.7*) TORCH_BACKEND="${TORCH_BACKEND:-cu127}" ;;
    12.8* | 12.9*) TORCH_BACKEND="${TORCH_BACKEND:-cu128}" ;;
    *)
      echo "[cuda] Warning: unsupported CUDA ${cuda_version}, defaulting to cu128" >&2
      TORCH_BACKEND="${TORCH_BACKEND:-cu128}"
      ;;
  esac

  PYTORCH_CUDA_INDEX_URL="${PYTORCH_CUDA_INDEX_URL:-https://download.pytorch.org/whl/${TORCH_BACKEND}}"
  export TORCH_BACKEND PYTORCH_CUDA_INDEX_URL
}
