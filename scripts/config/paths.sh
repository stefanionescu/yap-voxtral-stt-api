#!/usr/bin/env bash
set -euo pipefail

# Repo root, derived from this file location: scripts/config/paths.sh -> repo root.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"

# Common paths (overridable via env where it matters).
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"

SERVER_LOG_FILE="${SERVER_LOG_FILE:-${ROOT_DIR}/server.log}"
SERVER_PID_FILE="${SERVER_PID_FILE:-${ROOT_DIR}/server.pid}"
TAIL_PID_FILE="${TAIL_PID_FILE:-${ROOT_DIR}/tail.pid}"
LAUNCHER_PID_FILE="${LAUNCHER_PID_FILE:-${ROOT_DIR}/launcher.pid}"
LOG_TRIM_PID_FILE="${LOG_TRIM_PID_FILE:-${ROOT_DIR}/logtrim.pid}"
