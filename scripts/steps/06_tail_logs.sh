#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/lib/log.sh"

TAIL_LOGS="${TAIL_LOGS:-1}"
TAIL_PID_FILE="${ROOT_DIR}/tail.pid"

if [[ ${TAIL_LOGS} == "0" ]]; then
  log_info "[logs] TAIL_LOGS=0 (not tailing server.log)"
  exit 0
fi

log_blank
log_info "[logs] tail -f ${ROOT_DIR}/server.log"
log_info "[logs] stop: bash scripts/stop.sh"
log_blank

tail -f "${ROOT_DIR}/server.log" &
tail_pid=$!
echo "${tail_pid}" >"${TAIL_PID_FILE}"
trap 'rm -f "${TAIL_PID_FILE}" >/dev/null 2>&1 || true' EXIT
wait "${tail_pid}"
