#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  log_err "[warmup] ✗ venv not found at ${VENV_DIR}. Run: bash scripts/main.sh"
  exit 1
fi

log_info "[warmup] Installing dev deps..."
"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements-dev.txt" >/dev/null

log_section "[warmup] Running warmup client..."
cd "${ROOT_DIR}"
"${VENV_DIR}/bin/python" -m tests.e2e.warmup

log_section "[warmup] Running bench test (concurrency=8)..."
"${VENV_DIR}/bin/python" -m tests.e2e.bench --n 8 --concurrency 8

log_info "[warmup] Done"
