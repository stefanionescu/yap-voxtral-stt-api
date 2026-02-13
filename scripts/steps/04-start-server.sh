#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/server.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log.sh"

pid_file="${SERVER_PID_FILE}"

if [[ -f ${pid_file} ]]; then
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -n ${pid} ]] && ps -p "${pid}" >/dev/null 2>&1; then
    log_err "[start] ✗ Server already running (PID=${pid}). Use scripts/stop.sh first."
    exit 1
  fi
  rm -f "${pid_file}" || true
fi

log_section "[start] Starting server"
log_info "[start] bind=${SERVER_BIND_HOST}:${SERVER_PORT}"

# Start as a new session so it can be killed via process group.
setsid "${VENV_DIR}/bin/python" -m uvicorn src.server:app \
  --app-dir "${ROOT_DIR}" \
  --host "${SERVER_BIND_HOST}" \
  --port "${SERVER_PORT}" \
  --workers 1 >>"${SERVER_LOG_FILE}" 2>&1 &

pid=$!
echo "${pid}" >"${pid_file}"
log_info "[start] pid=${pid}"
