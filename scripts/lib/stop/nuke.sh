#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../../config/paths.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../../config/stop.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log/logging.sh"

main() {
  log_info "[stop] Nuke: wiping repo runtime + caches"

  for d in "${NUKE_REPO_DIRS[@]}"; do
    rm -rf "${d}" || true
  done
  for f in "${NUKE_REPO_FILES[@]}"; do
    rm -f "${f}" || true
  done

  for d in "${NUKE_HOME_DIRS[@]}"; do
    rm -rf "${d}" || true
  done

  # Remove Python bytecode caches in the repo to avoid stale folder noise.
  find "${ROOT_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
  find "${ROOT_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

  # Clean up empty directories that were created only to hold __pycache__.
  find "${ROOT_DIR}/src" -type d -empty -delete 2>/dev/null || true
  find "${ROOT_DIR}/tests" -type d -empty -delete 2>/dev/null || true
}

main "$@"
