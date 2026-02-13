#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log.sh"

log_info "[restart] Restarting server..."

bash "${SCRIPT_DIR}/stop.sh" "$@"
exec bash "${SCRIPT_DIR}/main.sh" "$@"
