#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/lib/log.sh"

VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"
REQ_FILE="${REQ_FILE:-${ROOT_DIR}/requirements.txt}"

# CUDA 13 torch wheels index.
PYTORCH_CUDA_INDEX_URL="${PYTORCH_CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu130}"

log_section "[deps] Installing dependencies"

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
