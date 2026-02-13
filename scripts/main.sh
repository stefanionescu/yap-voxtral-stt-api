#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

# Server launcher (FastAPI + vLLM realtime).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${ROOT_DIR}/scripts/lib/log.sh"

LAUNCHER_PID_FILE="${ROOT_DIR}/launcher.pid"
echo "$$" >"${LAUNCHER_PID_FILE}"
trap 'rm -f "${LAUNCHER_PID_FILE}" >/dev/null 2>&1 || true' EXIT

log_info "[main] Voxtral STT server"

bash "${ROOT_DIR}/scripts/steps/01_require_env.sh"
bash "${ROOT_DIR}/scripts/steps/02_venv.sh"
bash "${ROOT_DIR}/scripts/steps/03_install_deps.sh"
bash "${ROOT_DIR}/scripts/steps/04_start_server.sh"
bash "${ROOT_DIR}/scripts/steps/05_wait_health.sh"
bash "${ROOT_DIR}/scripts/steps/06_tail_logs.sh"
