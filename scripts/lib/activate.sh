#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/helpers.sh"

PY_BIN="$(choose_python)"

if [[ ! -d ${VENV_DIR} ]]; then
  "${PY_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

echo "Activated venv: ${VENV_DIR}"
