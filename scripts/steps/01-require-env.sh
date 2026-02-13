#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log.sh"

require_env() {
  local name="$1"
  if [[ -z ${!name:-} ]]; then
    log_err "[env] ✗ Missing required env var: ${name}"
    exit 1
  fi
}

require_env "VOXTRAL_API_KEY"
