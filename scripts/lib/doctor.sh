#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv}"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "[doctor] ✗ venv not found at ${VENV_DIR} (run: bash scripts/main.sh)" >&2
  exit 1
fi

echo "[doctor] Host"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
else
  echo "[doctor] ✗ nvidia-smi not found" >&2
  exit 2
fi

echo
echo "[doctor] Python"
"${VENV_DIR}/bin/python" -V

echo
echo "[doctor] CUDA (torch)"
TORCH_CUDA="$("${VENV_DIR}/bin/python" - <<'PY'
import torch
print(torch.version.cuda or "")
PY
)"

if [[ -z "${TORCH_CUDA}" ]]; then
  echo "[doctor] ✗ torch.version.cuda is empty (CPU-only torch?)" >&2
  exit 3
fi

echo "[doctor] torch.version.cuda=${TORCH_CUDA}"

case "${TORCH_CUDA}" in
  13.*)
    echo "[doctor] ✓ CUDA 13 detected"
    ;;
  *)
    echo "[doctor] ✗ expected CUDA 13.x, got '${TORCH_CUDA}'" >&2
    exit 4
    ;;
esac

echo
echo "[doctor] vLLM"
"${VENV_DIR}/bin/python" - <<'PY'
import vllm
print(vllm.__version__)
PY

echo
echo "[doctor] NVRTC"
if command -v ldconfig >/dev/null 2>&1; then
  if ldconfig -p 2>/dev/null | awk '/libnvrtc\\.so/ {found=1} END {exit !found}'; then
    echo "[doctor] ✓ libnvrtc.so present (ldconfig)"
    exit 0
  fi
fi

for p in \
  "/usr/local/cuda/lib64/libnvrtc.so" \
  "/usr/lib/x86_64-linux-gnu/libnvrtc.so" \
  "/usr/local/cuda/targets/x86_64-linux/lib/libnvrtc.so"; do
  if [[ -f "${p}" ]]; then
    echo "[doctor] ✓ libnvrtc.so present (${p})"
    exit 0
  fi
done

echo "[doctor] ✗ libnvrtc.so not found" >&2
exit 5

