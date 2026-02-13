#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/lib/log.sh"

VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"

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

py="$(choose_python)"
if [[ ! -d ${VENV_DIR} ]]; then
  log_info "[venv] Creating venv at ${VENV_DIR}"
  "${py}" -m venv "${VENV_DIR}"
fi
