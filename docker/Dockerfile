ARG CUDA_VERSION=12.8.0
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG TORCH_BACKEND=cu128
ARG PYTORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/${TORCH_BACKEND}
ARG VLLM_WHEEL_URL=https://github.com/vllm-project/vllm/releases/download/v0.16.0/vllm-0.16.0-cp38-abi3-manylinux_2_31_x86_64.whl

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-dev python3.11-venv python3-pip \
    ca-certificates git ffmpeg ninja-build build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt

# Install pinned runtime dependencies into the venv. CUDA torch wheels are
# provided via PYTORCH_CUDA_INDEX_URL (defaults to cu128).
# vLLM is installed separately from its GitHub release wheel before requirements.txt
# so that the pinned version is satisfied when pip resolves the remaining deps.
RUN python3.11 -m pip install -U pip \
    && python3.11 -m pip install "uv==0.8.3" \
    && python3.11 -m venv /workspace/.venv \
    && uv pip install --python /workspace/.venv/bin/python -U pip \
    && uv pip install --python /workspace/.venv/bin/python "${VLLM_WHEEL_URL}" \
    && uv pip install --python /workspace/.venv/bin/python -r /workspace/requirements.txt \
        --extra-index-url "${PYTORCH_CUDA_INDEX_URL}" \
        --index-strategy unsafe-best-match \
        --torch-backend="${TORCH_BACKEND}"

# Build flash-attn from source (no prebuilt wheel for torch 2.10 yet).
# --no-build-isolation is required so the build can find the already-installed torch.
RUN MAX_JOBS=4 uv pip install --python /workspace/.venv/bin/python \
    flash-attn==2.8.3 --no-build-isolation

# Verify flash-attn is importable.
RUN /workspace/.venv/bin/python -c \
    "from flash_attn import flash_attn_func; print('flash-attn OK')"

COPY src /workspace/src

ENV VIRTUAL_ENV=/workspace/.venv
ENV PATH="/workspace/.venv/bin:${PATH}"

ENV SERVER_BIND_HOST=0.0.0.0
ENV SERVER_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
