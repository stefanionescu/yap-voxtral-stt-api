FROM nvidia/cuda:13.0.0-runtime-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip ca-certificates git ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt

# NOTE: Voxtral recommends vLLM from wheels.vllm.ai/nightly. We keep the Dockerfile
# scaffolding minimal; tune torch/vLLM pins for your CUDA driver stack.
RUN python3.11 -m pip install -U pip \
    && python3.11 -m pip install -r /workspace/requirements.txt

COPY src /workspace/src

ENV SERVER_BIND_HOST=0.0.0.0
ENV SERVER_PORT=8000

EXPOSE 8000

CMD ["python3.11", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]

