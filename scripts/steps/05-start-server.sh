#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/server.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/logs.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/helpers.sh"

pid_file="${SERVER_PID_FILE}"

if is_pid_alive "${pid_file}"; then
  log_err "[start] ✗ Server already running (PID=${PID_VALUE}). Use scripts/stop.sh first."
  exit 1
fi
rm -f "${pid_file}" || true

log_section "[start] Starting server"
log_info "[start] bind=${SERVER_BIND_HOST}:${SERVER_PORT}"

# Ensure log directory exists (SERVER_LOG_FILE may be overridden to a subdir path).
mkdir -p "$(dirname "${SERVER_LOG_FILE}")" >/dev/null 2>&1 || true

# Trim oversized server.log before launching (keeps disk usage bounded across long runs).
max_log_bytes="${SERVER_LOG_MAX_BYTES}"
trim_log_file "${SERVER_LOG_FILE}" "${max_log_bytes}"

# Ensure no stale log-trimmer is running from a previous run.
if is_pid_alive "${LOG_TRIM_PID_FILE}"; then
  log_warn "[start] Stopping stale log trimmer PID=${PID_VALUE}"
  kill -TERM "${PID_VALUE}" 2>/dev/null || true
fi
rm -f "${LOG_TRIM_PID_FILE}" >/dev/null 2>&1 || true

# Start as a new session so it can be killed via process group.
setsid nohup "${VENV_DIR}/bin/python" -m uvicorn src.server:app \
  --app-dir "${ROOT_DIR}" \
  --host "${SERVER_BIND_HOST}" \
  --port "${SERVER_PORT}" \
  --workers 1 </dev/null >>"${SERVER_LOG_FILE}" 2>&1 &

pid=$!
echo "${pid}" >"${pid_file}"
log_info "[start] pid=${pid}"

# Start a background log trimmer so server.log stays bounded even during long runs.
if [[ ${max_log_bytes} =~ ^[0-9]+$ ]] && [[ ${max_log_bytes} -gt 0 ]]; then
  trim_interval_s="${SERVER_LOG_TRIM_INTERVAL_S}"

  setsid nohup bash "${ROOT_DIR}/scripts/lib/log/trimmer.sh" \
    "${SERVER_LOG_FILE}" "${max_log_bytes}" "${trim_interval_s}" \
    </dev/null >/dev/null 2>&1 &
  trim_pid=$!
  echo "${trim_pid}" >"${LOG_TRIM_PID_FILE}"
  log_info "[start] log_trimmer_pid=${trim_pid} (interval=${trim_interval_s}s, max_bytes=${max_log_bytes})"
fi
