#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"

RUN_FIX="${RUN_FIX:-0}"

run_quiet() {
  local label="$1"
  shift
  local tmp
  tmp="$(mktemp)"
  if "$@" >"$tmp" 2>&1; then
    rm -f "$tmp"
    return 0
  fi
  echo "[lint] ${label} failed" >&2
  cat "$tmp" >&2
  rm -f "$tmp"
  return 1
}

main() {
  cd "${ROOT_DIR}"

  if ! python -m isort --version >/dev/null 2>&1; then
    echo "isort not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi

  if [[ ${RUN_FIX} -eq 1 ]]; then
    run_quiet "isort" python -m isort --settings-path pyproject.toml "${ROOT_DIR}"
  else
    run_quiet "isort" python -m isort --settings-path pyproject.toml --check-only --diff "${ROOT_DIR}"
  fi

  if ! python -m ruff --version >/dev/null 2>&1; then
    echo "ruff not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi

  if [[ ${RUN_FIX} -eq 1 ]]; then
    run_quiet "ruff format" python -m ruff format --config "${ROOT_DIR}/pyproject.toml" "${ROOT_DIR}"
  else
    run_quiet "ruff format" python -m ruff format --config "${ROOT_DIR}/pyproject.toml" --check "${ROOT_DIR}"
  fi

  if [[ ${RUN_FIX} -eq 1 ]]; then
    run_quiet "ruff lint" python -m ruff check --config "${ROOT_DIR}/pyproject.toml" --fix "${ROOT_DIR}"
  else
    run_quiet "ruff lint" python -m ruff check --config "${ROOT_DIR}/pyproject.toml" "${ROOT_DIR}"
  fi

  if ! command -v lint-imports >/dev/null 2>&1; then
    echo "lint-imports not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi
  run_quiet "import-linter" lint-imports

  run_quiet "import-cycles" python "${ROOT_DIR}/linting/import_cycles.py"
  run_quiet "all-at-bottom" python "${ROOT_DIR}/linting/all_at_bottom.py"

  PY_DIRS=()
  [[ -d "${ROOT_DIR}/src" ]] && PY_DIRS+=("${ROOT_DIR}/src")
  [[ -d "${ROOT_DIR}/tests" ]] && PY_DIRS+=("${ROOT_DIR}/tests")
  if [[ ${#PY_DIRS[@]} -gt 0 ]]; then
    if ! python -m mypy --version >/dev/null 2>&1; then
      echo "mypy not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
      exit 1
    fi
    run_quiet "mypy" python -m mypy --follow-imports=skip "${PY_DIRS[@]}"
  fi

  run_quiet "file-length" python "${ROOT_DIR}/linting/file_length.py"
  run_quiet "function-length" python "${ROOT_DIR}/linting/function_length.py"
  run_quiet "one-class-per-file" python "${ROOT_DIR}/linting/one_class_per_file.py"
  run_quiet "no-runtime-singletons" python "${ROOT_DIR}/linting/no_runtime_singletons.py"
  run_quiet "no-lazy-module-loading" python "${ROOT_DIR}/linting/no_lazy_module_loading.py"
  run_quiet "no-local-imports" python "${ROOT_DIR}/linting/no_local_imports.py"
  run_quiet "no-legacy-markers" python "${ROOT_DIR}/linting/no_legacy_markers.py"
  run_quiet "dockerignore-policy" python "${ROOT_DIR}/linting/dockerignore_policy.py"
  run_quiet "single-file-folders" python "${ROOT_DIR}/linting/single_file_folders.py"
  run_quiet "prefix-collisions" python "${ROOT_DIR}/linting/prefix_collisions.py"
  run_quiet "no-inline-python" python "${ROOT_DIR}/linting/no_inline_python.py"
  run_quiet "file-names" python "${ROOT_DIR}/linting/file_names.py"
}

main "$@"
