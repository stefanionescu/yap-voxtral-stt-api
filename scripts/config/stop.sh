#!/usr/bin/env bash
set -euo pipefail

# Cache and runtime directories removed during `--nuke`.
NUKE_REPO_DIRS=(
  "${ROOT_DIR}/.venv"
  "${ROOT_DIR}/models"
  "${ROOT_DIR}/logs"
)

NUKE_REPO_FILES=(
  "${ROOT_DIR}/server.log"
)

NUKE_HOME_DIRS=(
  "${HOME}/.cache/huggingface"
  "${HOME}/.cache/torch"
  "${HOME}/.cache/vllm"
  "${HOME}/.cache/triton"
  "${HOME}/.cache/uv"
  "${HOME}/.cache/pip"
)

