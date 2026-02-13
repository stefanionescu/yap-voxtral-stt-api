#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/lib/log.sh"

SERVER_PORT="${SERVER_PORT:-8000}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${SERVER_PORT}/healthz}"
HEALTH_TIMEOUT_S="${HEALTH_TIMEOUT_S:-600}"

log_info "[health] Waiting for health: ${HEALTH_URL}"

deadline=$((SECONDS + HEALTH_TIMEOUT_S))
while ((SECONDS <= deadline)); do
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
      log_info "[health] ✓ healthy"
      exit 0
    fi
  fi
  sleep 1
done

log_err "[health] ✗ server did not become healthy within ${HEALTH_TIMEOUT_S}s"
log_err "[health] tail -n 200 ${ROOT_DIR}/server.log"
exit 1

