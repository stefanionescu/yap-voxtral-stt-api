#!/usr/bin/env bash
set -euo pipefail

# Runtime dependency install configuration.
REQ_FILE="${REQ_FILE:-${ROOT_DIR}/requirements.txt}"

# CUDA 12.8 torch wheels index.
PYTORCH_CUDA_INDEX_URL="${PYTORCH_CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu128}"

# uv --torch-backend flag value.
TORCH_BACKEND="${TORCH_BACKEND:-cu128}"

# vLLM wheel (GitHub release asset — not on PyPI for this version).
VLLM_WHEEL_URL="${VLLM_WHEEL_URL:-https://github.com/vllm-project/vllm/releases/download/v0.16.0/vllm-0.16.0-cp38-abi3-manylinux_2_31_x86_64.whl}"

# flash-attn version (installed separately due to --no-build-isolation).
FLASH_ATTN_VERSION="${FLASH_ATTN_VERSION:-2.8.3}"
