#!/usr/bin/env bash
set -euo pipefail

log_blank() { echo ""; }
log_info() { echo "$@"; }
log_warn() { echo "$@" >&2; }
log_err() { echo "$@" >&2; }
log_section() {
  echo ""
  echo "$@"
}
