#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/config/paths.sh"
# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/log.sh"

NUKE_FLAG=0
for arg in "$@"; do
  case "${arg}" in
    --nuke)
      NUKE_FLAG=1
      ;;
  esac
done

# Backwards-compatible toggle.
if [[ ${FULL_CLEANUP:-0} == "1" ]]; then
  NUKE_FLAG=1
fi

if [[ ${NUKE_FLAG} == "1" && ${NUKE:-0} != "1" ]]; then
  log_err "[stop] ✗ Refusing to nuke without explicit NUKE=1"
  log_err "[stop]   Example: NUKE=1 bash scripts/stop.sh --nuke"
  exit 2
fi

main() {
  bash "${ROOT_DIR}/scripts/lib/stop-pids.sh"

  if [[ ${NUKE_FLAG} == "1" ]]; then
    bash "${ROOT_DIR}/scripts/lib/stop-nuke.sh"
  fi

  log_info "[stop] Done"
}

main "$@"
