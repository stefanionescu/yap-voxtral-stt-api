#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

# Voxtral STT server launcher (vLLM realtime, FastAPI /ws envelope).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/lib/log.sh"

SERVER_BIND_HOST="${SERVER_BIND_HOST:-0.0.0.0}"
SERVER_PORT="${SERVER_PORT:-8000}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${SERVER_PORT}/healthz}"
HEALTH_TIMEOUT_S="${HEALTH_TIMEOUT_S:-600}"

VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"
VLLM_WHEELS_INDEX_URL="${VLLM_WHEELS_INDEX_URL:-https://wheels.vllm.ai/nightly/cu130}"

require_env() {
  local name="$1"
  if [[ -z ${!name:-} ]]; then
    log_err "[main] ✗ Missing required env var: ${name}"
    exit 1
  fi
}

choose_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  echo "python"
}

ensure_venv() {
  local py
  py="$(choose_python)"
  if [[ ! -d ${VENV_DIR} ]]; then
    log_info "[main] Creating venv at ${VENV_DIR}"
    "${py}" -m venv "${VENV_DIR}"
  fi
}

install_deps() {
  log_section "[main] Installing dependencies"

  if command -v uv >/dev/null 2>&1; then
    log_info "[deps] Using uv pip (recommended for vLLM nightlies)"
    uv pip install --python "${VENV_DIR}/bin/python" -U pip
    uv pip install --python "${VENV_DIR}/bin/python" -r "${ROOT_DIR}/requirements.txt" \
      --extra-index-url "${VLLM_WHEELS_INDEX_URL}" \
      --torch-backend=cu130
  else
    log_warn "[deps] uv not found; falling back to pip. You may need to install a compatible CUDA torch wheel manually."
    "${VENV_DIR}/bin/python" -m pip install -U pip
    "${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements.txt"
  fi
}

guard_pid() {
  local pid_file="${ROOT_DIR}/server.pid"
  if [[ ! -f ${pid_file} ]]; then
    return
  fi
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -n ${pid} ]] && ps -p "${pid}" >/dev/null 2>&1; then
    log_err "[main] ✗ Server already running (PID=${pid}). Use scripts/stop.sh first."
    exit 1
  fi
  rm -f "${pid_file}" || true
}

start_server() {
  guard_pid

  log_section "[main] Starting server"
  log_info "[main] bind=${SERVER_BIND_HOST}:${SERVER_PORT}"

  # Start as a new session so Ctrl+C doesn't kill the server.
  setsid "${VENV_DIR}/bin/python" -m uvicorn src.server:app \
    --app-dir "${ROOT_DIR}" \
    --host "${SERVER_BIND_HOST}" \
    --port "${SERVER_PORT}" \
    --workers 1 >>"${ROOT_DIR}/server.log" 2>&1 &

  local pid=$!
  echo "${pid}" >"${ROOT_DIR}/server.pid"
  log_info "[main] pid=${pid}"
}

await_health() {
  log_info "[main] Waiting for health: ${HEALTH_URL}"
  local deadline=$((SECONDS + HEALTH_TIMEOUT_S))
  while ((SECONDS <= deadline)); do
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
        log_info "[main] ✓ healthy"
        return
      fi
    fi
    sleep 1
  done

  log_err "[main] ✗ server did not become healthy within ${HEALTH_TIMEOUT_S}s"
  log_err "[main] tail -n 200 ${ROOT_DIR}/server.log"
  exit 1
}

main() {
  log_info "[main] Voxtral STT server"
  require_env "VOXTRAL_API_KEY"

  ensure_venv
  install_deps
  start_server
  await_health

  log_blank
  log_info "[main] Logs: tail -f ${ROOT_DIR}/server.log"
  log_info "[main] Stop: bash scripts/stop.sh"
  log_blank

  tail -f "${ROOT_DIR}/server.log"
}

main "$@"
