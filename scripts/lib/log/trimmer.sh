#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091
set -euo pipefail

# Background log trimmer: keeps a single log file bounded by trimming to the last N bytes.
# This is intentionally simple (no rotations) to match "tail server.log" workflows.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../helpers.sh"

log_file="${1:-}"
max_keep_bytes="${2:-}"
interval_s="${3:-}"

if [[ -z ${log_file} ]] || [[ -z ${max_keep_bytes} ]] || [[ -z ${interval_s} ]]; then
  echo "[logtrim] usage: trimmer.sh <log_file> <max_keep_bytes> <interval_s>" >&2
  exit 2
fi

if ! [[ ${max_keep_bytes} =~ ^[0-9]+$ ]]; then
  echo "[logtrim] max_keep_bytes must be an integer: ${max_keep_bytes}" >&2
  exit 2
fi

if ! [[ ${interval_s} =~ ^[0-9]+$ ]]; then
  echo "[logtrim] interval_s must be an integer: ${interval_s}" >&2
  exit 2
fi

if [[ ${max_keep_bytes} -le 0 ]]; then
  # Disabled.
  exit 0
fi

touch "${log_file}" 2>/dev/null || true

while true; do
  trim_log_file "${log_file}" "${max_keep_bytes}"
  sleep "${interval_s}"
done
