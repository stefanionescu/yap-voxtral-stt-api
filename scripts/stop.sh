#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/lib/log.sh"

FULL_CLEANUP="${FULL_CLEANUP:-0}"

stop_server() {
  local pid_file="${ROOT_DIR}/server.pid"
  if [[ ! -f ${pid_file} ]]; then
    log_info "[stop] No server.pid found"
    return
  fi
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z ${pid} ]]; then
    rm -f "${pid_file}" || true
    return
  fi

  if ps -p "${pid}" >/dev/null 2>&1; then
    log_info "[stop] Stopping server PID=${pid}"
    kill -TERM "-${pid}" 2>/dev/null || true
    sleep 1
  fi

  rm -f "${pid_file}" || true
}

cleanup() {
  if [[ ${FULL_CLEANUP} == "0" ]]; then
    return
  fi
  log_info "[stop] Full cleanup: wiping venv/models/logs"
  rm -rf "${ROOT_DIR}/.venv" || true
  rm -rf "${ROOT_DIR}/models" || true
  rm -rf "${ROOT_DIR}/logs" || true
  rm -f "${ROOT_DIR}/server.log" || true
}

main() {
  stop_server
  cleanup
  log_info "[stop] Done"
}

main "$@"
