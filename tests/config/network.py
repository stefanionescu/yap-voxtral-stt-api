from __future__ import annotations

# Heuristics for cloud endpoints (used for display/diagnostics only).
LOCALHOST_IDENTIFIERS = ("localhost", "127.0.0.1")
PRIVATE_IP_BLOCKS = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.3")

CLOUD_HOST_MARKERS = (
    "runpod",
    "modal",
    "lambda",
    "vast",
    "replicate",
    "aws",
    "ec2",
    "gcp",
    "azure",
)

__all__ = ["CLOUD_HOST_MARKERS", "LOCALHOST_IDENTIFIERS", "PRIVATE_IP_BLOCKS"]
