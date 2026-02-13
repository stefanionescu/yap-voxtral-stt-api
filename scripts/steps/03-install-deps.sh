#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/deps.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log.sh"

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
