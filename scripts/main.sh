#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

# Server launcher (FastAPI + vLLM realtime).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log.sh"

echo "$$" >"${LAUNCHER_PID_FILE}"
trap 'rm -f "${LAUNCHER_PID_FILE}" >/dev/null 2>&1 || true' EXIT

log_info "[main] Voxtral STT server"

bash "${ROOT_DIR}/scripts/steps/01-require-env.sh"
bash "${ROOT_DIR}/scripts/steps/02-venv.sh"
bash "${ROOT_DIR}/scripts/steps/03-install-deps.sh"
bash "${ROOT_DIR}/scripts/steps/04-start-server.sh"
bash "${ROOT_DIR}/scripts/steps/05-wait-health.sh"
bash "${ROOT_DIR}/scripts/steps/06-tail-logs.sh"
