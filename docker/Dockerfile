FROM nvidia/cuda:13.0.0-runtime-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG PYTORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu130

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip ca-certificates git ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt

# Install pinned runtime dependencies into the venv. CUDA 13 torch wheels are
# provided via PYTORCH_CUDA_INDEX_URL.
RUN python3.11 -m pip install -U pip \
    && python3.11 -m pip install "uv==0.8.3" \
    && python3.11 -m venv /workspace/.venv \
    && uv pip install --python /workspace/.venv/bin/python -U pip \
    && uv pip install --python /workspace/.venv/bin/python -r /workspace/requirements.txt \
        --extra-index-url "${PYTORCH_CUDA_INDEX_URL}" \
        --index-strategy unsafe-best-match \
        --torch-backend=cu130

COPY src /workspace/src

ENV VIRTUAL_ENV=/workspace/.venv
ENV PATH="/workspace/.venv/bin:${PATH}"

ENV SERVER_BIND_HOST=0.0.0.0
ENV SERVER_PORT=8000
ENV VLLM_ATTENTION_BACKEND=FLASH_ATTN

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
