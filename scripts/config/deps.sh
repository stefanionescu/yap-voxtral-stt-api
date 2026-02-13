#!/usr/bin/env bash
set -euo pipefail

# Runtime dependency install configuration.
REQ_FILE="${REQ_FILE:-${ROOT_DIR}/requirements.txt}"

# CUDA 13 torch wheels index.
PYTORCH_CUDA_INDEX_URL="${PYTORCH_CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu130}"

