#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/helpers.sh"

py="$(choose_python)"
if [[ ! -d ${VENV_DIR} ]]; then
  log_info "[venv] Creating venv at ${VENV_DIR}"
  "${py}" -m venv "${VENV_DIR}"
fi
