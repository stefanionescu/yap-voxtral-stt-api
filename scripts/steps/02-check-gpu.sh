#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  log_err "[gpu] ✗ nvidia-smi not found (cannot verify GPU profile)"
  exit 1
fi

gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 | tr -d '\\r' | sed 's/^ *//; s/ *$//')"
if [[ -z ${gpu_name} ]]; then
  log_err "[gpu] ✗ failed to read GPU name via nvidia-smi"
  exit 1
fi

case "${gpu_name}" in
  *"L40S"*|*"L40"*|*"H100"*|*"A100"*|*"B200"*|*"RTX 6000"*|*"RTX 9000"*)
    log_info "[gpu] ✓ supported GPU detected: ${gpu_name}"
    ;;
  *)
    log_err "[gpu] ✗ unsupported/unknown GPU: ${gpu_name}"
    log_err "[gpu]   Add a profile for this GPU."
    exit 1
    ;;
esac
