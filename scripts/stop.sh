#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${ROOT_DIR}/scripts/lib/log.sh"

NUKE_FLAG=0
for arg in "$@"; do
  case "${arg}" in
    --nuke)
      NUKE_FLAG=1
      ;;
  esac
done

# Backwards-compatible toggle.
if [[ ${FULL_CLEANUP:-0} == "1" ]]; then
  NUKE_FLAG=1
fi

if [[ ${NUKE_FLAG} == "1" && ${NUKE:-0} != "1" ]]; then
  log_err "[stop] ✗ Refusing to nuke without explicit NUKE=1"
  log_err "[stop]   Example: NUKE=1 bash scripts/stop.sh --nuke"
  exit 2
fi

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

cleanup_nuke() {
  log_info "[stop] Nuke: wiping repo runtime + caches"

  rm -rf "${ROOT_DIR}/.venv" || true
  rm -rf "${ROOT_DIR}/models" || true
  rm -rf "${ROOT_DIR}/logs" || true
  rm -f "${ROOT_DIR}/server.log" || true

  rm -rf "${HOME}/.cache/huggingface" || true
  rm -rf "${HOME}/.cache/torch" || true
  rm -rf "${HOME}/.cache/vllm" || true
  rm -rf "${HOME}/.cache/triton" || true
  rm -rf "${HOME}/.cache/uv" || true
  rm -rf "${HOME}/.cache/pip" || true
}

main() {
  stop_pid_file "${ROOT_DIR}/tail.pid" "log tail" "0"
  stop_pid_file "${ROOT_DIR}/launcher.pid" "launcher" "0"
  stop_pid_file "${ROOT_DIR}/server.pid" "server" "1"

  if [[ ${NUKE_FLAG} == "1" ]]; then
    cleanup_nuke
  fi

  log_info "[stop] Done"
}

main "$@"
