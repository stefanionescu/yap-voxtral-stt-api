#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/log.sh"

VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  log_err "[warmup] ✗ venv not found at ${VENV_DIR}. Run: bash scripts/main.sh"
  exit 1
fi

log_info "[warmup] Installing dev deps (clients)"
"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements-dev.txt" >/dev/null

log_section "[warmup] Running warmup client"
"${VENV_DIR}/bin/python" tests/e2e/warmup.py

log_section "[warmup] Running small bench (concurrency=8)"
"${VENV_DIR}/bin/python" tests/e2e/bench.py --requests 8 --concurrency 8

log_info "[warmup] Done"
