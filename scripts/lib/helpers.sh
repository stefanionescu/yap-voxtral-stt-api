#!/usr/bin/env bash
# Shared helper functions for scripts.

# Select the best available Python binary.
choose_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  echo "python"
}

# Run a command quietly; show output only on failure.
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

# Check if PID in a file is alive. Returns 0 if alive, 1 otherwise.
# Sets PID_VALUE to the pid read from the file.
is_pid_alive() {
  local pid_file="$1"
  PID_VALUE=""
  [[ -f ${pid_file} ]] || return 1
  PID_VALUE="$(cat "${pid_file}" 2>/dev/null || true)"
  [[ -n ${PID_VALUE} ]] && ps -p "${PID_VALUE}" >/dev/null 2>&1
}

# Trim a log file to the last N bytes (in-place, preserves inode).
trim_log_file() {
  local log_file="$1"
  local max_bytes="$2"
  [[ -f ${log_file} ]] || return 0
  local size_bytes
  size_bytes="$(wc -c <"${log_file}" 2>/dev/null || echo 0)"
  if [[ ${size_bytes} =~ ^[0-9]+$ ]] && [[ ${size_bytes} -gt ${max_bytes} ]]; then
    local offset=$((size_bytes - max_bytes))
    local tmp_file="${log_file}.trim.$$"
    if tail -c "${max_bytes}" "${log_file}" >"${tmp_file}" 2>/dev/null; then
      cat "${tmp_file}" >"${log_file}" 2>/dev/null || true
      rm -f "${tmp_file}" >/dev/null 2>&1 || true
      local size_mb=$((max_bytes / 1024 / 1024))
      echo "[logtrim] Trimmed to latest ${size_mb}MB (removed ${offset} bytes)" >>"${log_file}"
    else
      rm -f "${tmp_file}" >/dev/null 2>&1 || true
    fi
  fi
}
