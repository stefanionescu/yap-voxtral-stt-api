from __future__ import annotations

# Benchmark jitter (avoid thundering-herd connection bursts).
JITTER_STEP_S: float = 0.02
JITTER_GROUP_SIZE: int = 16

# Handshake allowance added to computed session timeouts.
HANDSHAKE_ALLOWANCE_NO_WAIT_S: float = 5.0
HANDSHAKE_ALLOWANCE_WAIT_S: float = 10.0

# Finalization allowance (waiting for the server to emit transcription.done).
FINALIZE_ALLOWANCE_EXTRA_S: float = 30.0
FINALIZE_ALLOWANCE_CAP_S: float = 120.0

# Timeout computation safety margins.
COMPUTE_TIMEOUT_MIN_S: float = 30.0
COMPUTE_TIMEOUT_MAX_S: float = 600.0
COMPUTE_TIMEOUT_SAFETY_MULT: float = 2.0
COMPUTE_TIMEOUT_SAFETY_ADD_S: float = 5.0

__all__ = [
    "COMPUTE_TIMEOUT_MAX_S",
    "COMPUTE_TIMEOUT_MIN_S",
    "COMPUTE_TIMEOUT_SAFETY_ADD_S",
    "COMPUTE_TIMEOUT_SAFETY_MULT",
    "FINALIZE_ALLOWANCE_CAP_S",
    "FINALIZE_ALLOWANCE_EXTRA_S",
    "HANDSHAKE_ALLOWANCE_NO_WAIT_S",
    "HANDSHAKE_ALLOWANCE_WAIT_S",
    "JITTER_GROUP_SIZE",
    "JITTER_STEP_S",
]
