#!/usr/bin/env bash
set -euo pipefail

# Server log retention policy.
#
# We keep a single `server.log` file (for easy `tail -F`) and periodically trim
# it to the last N bytes so disk usage stays bounded across long runs.

# Keep the most recent 100MB.
SERVER_LOG_MAX_BYTES=104857600

# How often to enforce the size cap (seconds).
SERVER_LOG_TRIM_INTERVAL_S=30

