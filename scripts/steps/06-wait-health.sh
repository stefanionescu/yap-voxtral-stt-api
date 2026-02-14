#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/paths.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../config/server.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"

if ! command -v curl >/dev/null 2>&1; then
  log_err "[health] ✗ curl not found (required for health checks)"
  exit 1
fi

log_info "[health] Waiting for health: ${HEALTH_URL}"

deadline=$((SECONDS + HEALTH_TIMEOUT_S))
while ((SECONDS <= deadline)); do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    log_info "[health] ✓ healthy"
    exit 0
  fi
  sleep 1
done

log_err "[health] ✗ server did not become healthy within ${HEALTH_TIMEOUT_S}s"
log_err "[health] tail -n 200 ${SERVER_LOG_FILE}"
exit 1
