#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/lib/log.sh"

log_info "[restart] Restarting server..."

FULL_CLEANUP=0 bash "${SCRIPT_DIR}/stop.sh"
exec bash "${SCRIPT_DIR}/main.sh" "$@"
