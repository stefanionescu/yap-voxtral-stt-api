#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../../config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"

stop_pid_file() {
  local pid_file="$1"
  local label="$2"
  local kill_group="$3" # "1" -> kill process group (-PID)

  if [[ ! -f ${pid_file} ]]; then
    return
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z ${pid} ]]; then
    rm -f "${pid_file}" || true
    return
  fi

  if ps -p "${pid}" >/dev/null 2>&1; then
    log_info "[stop] Stopping ${label} PID=${pid}"
    if [[ ${kill_group} == "1" ]]; then
      kill -TERM "-${pid}" 2>/dev/null || true
    else
      kill -TERM "${pid}" 2>/dev/null || true
    fi

    for _ in $(seq 1 10); do
      if ! ps -p "${pid}" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done

    if ps -p "${pid}" >/dev/null 2>&1; then
      log_warn "[stop] Escalating ${label} kill (SIGKILL) PID=${pid}"
      if [[ ${kill_group} == "1" ]]; then
        kill -KILL "-${pid}" 2>/dev/null || true
      else
        kill -KILL "${pid}" 2>/dev/null || true
      fi
    fi
  fi

  rm -f "${pid_file}" || true
}

main() {
  stop_pid_file "${TAIL_PID_FILE}" "log tail" "0"
  stop_pid_file "${LAUNCHER_PID_FILE}" "launcher" "0"
  stop_pid_file "${LOG_TRIM_PID_FILE}" "log trimmer" "0"
  stop_pid_file "${SERVER_PID_FILE}" "server" "1"
}

main "$@"
