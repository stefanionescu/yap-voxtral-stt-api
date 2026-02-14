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

# Ensure log directory exists (SERVER_LOG_FILE may be overridden to a subdir path).
mkdir -p "$(dirname "${SERVER_LOG_FILE}")" >/dev/null 2>&1 || true

# Trim oversized server.log before launching (keeps disk usage bounded across long runs).
max_log_bytes="${SERVER_LOG_MAX_BYTES}"
if [[ -f ${SERVER_LOG_FILE} ]]; then
  size_bytes="$(wc -c <"${SERVER_LOG_FILE}" 2>/dev/null || echo 0)"
  if [[ ${size_bytes} =~ ^[0-9]+$ ]] && [[ ${size_bytes} -gt ${max_log_bytes} ]]; then
    offset=$((size_bytes - max_log_bytes))
    tmp_file="${ROOT_DIR}/.server.log.trim.$$"
    if tail -c "${max_log_bytes}" "${SERVER_LOG_FILE}" >"${tmp_file}" 2>/dev/null; then
      mv "${tmp_file}" "${SERVER_LOG_FILE}" 2>/dev/null || true
      size_mb=$((max_log_bytes / 1024 / 1024))
      echo "[server] Trimmed server.log to latest ${size_mb}MB (removed ${offset} bytes)" >>"${SERVER_LOG_FILE}"
    else
      rm -f "${tmp_file}" >/dev/null 2>&1 || true
    fi
  fi
fi

# Ensure no stale log-trimmer is running from a previous run.
if [[ -f ${LOG_TRIM_PID_FILE} ]]; then
  trim_pid="$(cat "${LOG_TRIM_PID_FILE}" 2>/dev/null || true)"
  if [[ -n ${trim_pid} ]] && ps -p "${trim_pid}" >/dev/null 2>&1; then
    log_warn "[start] Stopping stale log trimmer PID=${trim_pid}"
    kill -TERM "${trim_pid}" 2>/dev/null || true
    rm -f "${LOG_TRIM_PID_FILE}" >/dev/null 2>&1 || true
  else
    rm -f "${LOG_TRIM_PID_FILE}" >/dev/null 2>&1 || true
  fi
fi

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
