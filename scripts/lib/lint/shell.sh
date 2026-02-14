#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../../config/paths.sh"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../helpers.sh"

RUN_FIX="${RUN_FIX:-0}"

have() { command -v "$1" >/dev/null 2>&1; }

main() {
  cd "${ROOT_DIR}"

  # Prefer git-tracked files; fallback to find. Avoid bash 4+ mapfile for macOS compatibility.
  TMP_LIST="$(mktemp)"
  git -C "${ROOT_DIR}" ls-files -z "*.sh" >"${TMP_LIST}" 2>/dev/null || true
  if [[ ! -s ${TMP_LIST} ]]; then
    find "${ROOT_DIR}" -type f -name "*.sh" -print0 >"${TMP_LIST}"
  fi

  SHELL_FILES=()
  while IFS= read -r -d '' file; do
    if [[ ! -f ${file} ]]; then
      continue
    fi
    SHELL_FILES+=("${file}")
  done <"${TMP_LIST}"

  if [[ ${#SHELL_FILES[@]} -gt 0 ]]; then
    if ! have shellcheck; then
      echo "shellcheck not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
      rm -f "${TMP_LIST}"
      exit 1
    fi
    run_quiet "shellcheck" shellcheck -x "${SHELL_FILES[@]}"
  fi

  if have shfmt; then
    if [[ ${RUN_FIX} -eq 1 ]]; then
      run_quiet "shfmt" shfmt -w -i 2 -ci -s "${SHELL_FILES[@]}"
    else
      # -d outputs unified diff if formatting differs
      run_quiet "shfmt" shfmt -d -i 2 -ci -s "${SHELL_FILES[@]}"
    fi
  fi

  rm -f "${TMP_LIST}"
}

main "$@"
