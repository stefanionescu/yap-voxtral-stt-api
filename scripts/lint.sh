#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
RUN_FIX=0
ONLY=""

usage() {
  cat <<'USAGE'
Usage: scripts/lint.sh [--fix] [--only python|shell]

Runs linters across the repository:
  - Python: isort, ruff (lint + format), mypy (type check)
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
      if [[ -z $ONLY || ($ONLY != "python" && $ONLY != "shell") ]]; then
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

have() { command -v "$1" >/dev/null 2>&1; }

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

run_python() {
  if ! python -m isort --version >/dev/null 2>&1; then
    echo "isort not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi

  if [[ $RUN_FIX -eq 1 ]]; then
    run_quiet "isort" python -m isort --settings-path pyproject.toml "$ROOT_DIR"
  else
    run_quiet "isort" python -m isort --settings-path pyproject.toml --check-only --diff "$ROOT_DIR"
  fi

  if ! python -m ruff --version >/dev/null 2>&1; then
    echo "ruff not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi

  if [[ $RUN_FIX -eq 1 ]]; then
    run_quiet "ruff format" python -m ruff format --config "$ROOT_DIR/pyproject.toml" "$ROOT_DIR"
  else
    run_quiet "ruff format" python -m ruff format --config "$ROOT_DIR/pyproject.toml" --check "$ROOT_DIR"
  fi

  if [[ $RUN_FIX -eq 1 ]]; then
    run_quiet "ruff lint" python -m ruff check --config "$ROOT_DIR/pyproject.toml" --fix "$ROOT_DIR"
  else
    run_quiet "ruff lint" python -m ruff check --config "$ROOT_DIR/pyproject.toml" "$ROOT_DIR"
  fi

  if python -m src.scripts.validation_package importlinter; then
    run_quiet "import-linter" lint-imports
  fi

  run_quiet "import-cycles" python "$ROOT_DIR/linting/import_cycles.py"
  run_quiet "all-at-bottom" python "$ROOT_DIR/linting/all_at_bottom.py"

  if python -m src.scripts.validation_package mypy; then
    PY_DIRS=()
    [[ -d "$ROOT_DIR/src" ]] && PY_DIRS+=("$ROOT_DIR/src")
    [[ -d "$ROOT_DIR/tests" ]] && PY_DIRS+=("$ROOT_DIR/tests")
    if [[ ${#PY_DIRS[@]} -gt 0 ]]; then
      run_quiet "mypy" python -m mypy --follow-imports=skip "${PY_DIRS[@]}"
    fi
  fi

  run_quiet "file-length" python "$ROOT_DIR/linting/file_length.py"
  run_quiet "function-length" python "$ROOT_DIR/linting/function_length.py"
  run_quiet "one-class-per-file" python "$ROOT_DIR/linting/one_class_per_file.py"
  run_quiet "no-runtime-singletons" python "$ROOT_DIR/linting/no_runtime_singletons.py"
  run_quiet "no-lazy-module-loading" python "$ROOT_DIR/linting/no_lazy_module_loading.py"
  run_quiet "no-legacy-markers" python "$ROOT_DIR/linting/no_legacy_markers.py"
  run_quiet "dockerignore-policy" python "$ROOT_DIR/linting/dockerignore_policy.py"
  run_quiet "single-file-folders" python "$ROOT_DIR/linting/single_file_folders.py"
  run_quiet "prefix-collisions" python "$ROOT_DIR/linting/prefix_collisions.py"
  run_quiet "no-inline-python" python "$ROOT_DIR/linting/no_inline_python.py"
}

run_shell() {
  # Prefer git-tracked files; fallback to find. Avoid bash 4+ mapfile for macOS compatibility.
  TMP_LIST="$(mktemp)"
  git -C "$ROOT_DIR" ls-files -z "*.sh" >"$TMP_LIST" 2>/dev/null || true
  if [[ ! -s $TMP_LIST ]]; then
    find "$ROOT_DIR" -type f -name "*.sh" -print0 >"$TMP_LIST"
  fi

  SHELL_FILES=()
  while IFS= read -r -d '' file; do
    if [[ ! -f $file ]]; then
      continue
    fi
    SHELL_FILES+=("$file")
  done <"$TMP_LIST"

  if [[ ${#SHELL_FILES[@]} -gt 0 ]]; then
    if ! have shellcheck; then
      echo "shellcheck not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
      rm -f "$TMP_LIST"
      exit 1
    fi
    run_quiet "shellcheck" shellcheck -x "${SHELL_FILES[@]}"
  fi

  if have shfmt; then
    if [[ $RUN_FIX -eq 1 ]]; then
      run_quiet "shfmt" shfmt -w -i 2 -ci -s "${SHELL_FILES[@]}"
    else
      # -d outputs unified diff if formatting differs
      run_quiet "shfmt" shfmt -d -i 2 -ci -s "${SHELL_FILES[@]}"
    fi
  fi

  rm -f "$TMP_LIST"
}

case "$ONLY" in
  python)
    run_python
    ;;
  shell)
    run_shell
    ;;
  "")
    run_python
    run_shell
    ;;
esac
