#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/config/paths.sh"

RUN_FIX=0
ONLY=""

usage() {
  cat <<'USAGE'
Usage: scripts/lint.sh [--fix] [--only python|shell]

Runs linters across the repository:
  - Python: isort, ruff (lint + format), mypy (type check), import-linter, custom policies
  - Shell:  shellcheck (lint), shfmt (format if available)

Options:
  --fix              Apply auto-fixes (ruff format/check --fix, shfmt -w)
  --only python      Run only Python linters
  --only shell       Run only shell linters
  -h, --help         Show this help

Install dev tools:
  python -m pip install -r requirements-dev.txt

Shell formatting (optional):
  Install shfmt to enable shell formatting in --fix mode.
  macOS:  brew install shfmt
  Linux:  see https://github.com/mvdan/sh#shfmt for install options
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fix)
      RUN_FIX=1
      shift
      ;;
    --only)
      ONLY=${2:-}
      if [[ -z ${ONLY} || (${ONLY} != "python" && ${ONLY} != "shell") ]]; then
        echo "Error: --only expects 'python' or 'shell'" >&2
        exit 2
      fi
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

export RUN_FIX

case "${ONLY}" in
  python)
    bash "${ROOT_DIR}/scripts/lib/lint-python.sh"
    ;;
  shell)
    bash "${ROOT_DIR}/scripts/lib/lint-shell.sh"
    ;;
  "")
    bash "${ROOT_DIR}/scripts/lib/lint-python.sh"
    bash "${ROOT_DIR}/scripts/lib/lint-shell.sh"
    ;;
esac
