#!/usr/bin/env bash
set -euo pipefail

# Write all logs to stderr so stdout remains usable for structured outputs when needed.
log_info() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_warn() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_err() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }

log_blank() { echo >&2; }
log_section() {
  log_blank
  log_info "$@"
}
