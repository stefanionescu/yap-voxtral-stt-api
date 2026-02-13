#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/lib/log.sh"

SERVER_PORT="${SERVER_PORT:-8000}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${SERVER_PORT}/healthz}"

pid_file="${ROOT_DIR}/server.pid"
if [[ -f ${pid_file} ]]; then
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -n ${pid} ]] && ps -p "${pid}" >/dev/null 2>&1; then
    log_info "[status] running pid=${pid}"
  else
    log_warn "[status] stale pid file at ${pid_file}"
  fi
else
  log_info "[status] not running (no server.pid)"
fi

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    log_info "[status] health ok (${HEALTH_URL})"
  else
    log_warn "[status] health check failed (${HEALTH_URL})"
  fi
fi

log_info "[status] logs: tail -n 200 ${ROOT_DIR}/server.log"
