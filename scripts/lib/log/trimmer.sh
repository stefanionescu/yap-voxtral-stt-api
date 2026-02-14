#!/usr/bin/env bash
# shellcheck disable=SC1090
set -euo pipefail

# Background log trimmer: keeps a single log file bounded by trimming to the last N bytes.
# This is intentionally simple (no rotations) to match "tail server.log" workflows.

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
  if [[ -f ${log_file} ]]; then
    size_bytes="$(wc -c <"${log_file}" 2>/dev/null || echo 0)"
    if [[ ${size_bytes} =~ ^[0-9]+$ ]] && [[ ${size_bytes} -gt ${max_keep_bytes} ]]; then
      offset=$((size_bytes - max_keep_bytes))
      tmp_file="${log_file}.trim.$$"
      if tail -c "${max_keep_bytes}" "${log_file}" >"${tmp_file}" 2>/dev/null; then
        # Copy-truncate to keep the same inode (server writes via an open fd).
        cat "${tmp_file}" >"${log_file}" 2>/dev/null || true
        rm -f "${tmp_file}" >/dev/null 2>&1 || true
        size_mb=$((max_keep_bytes / 1024 / 1024))
        echo "[logtrim] Trimmed server.log to latest ${size_mb}MB (removed ${offset} bytes)" >>"${log_file}"
      else
        rm -f "${tmp_file}" >/dev/null 2>&1 || true
      fi
    fi
  fi
  sleep "${interval_s}"
done
