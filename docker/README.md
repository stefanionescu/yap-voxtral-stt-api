# Docker

This repository includes Docker scaffolding for running the server in a container.
It does not publish prebuilt images.

The image runs:
- CUDA 12.8 devel base by default (`nvidia/cuda:12.8.0-devel-ubuntu22.04`)
- Python 3.11
- Pinned Python deps from `requirements.txt`

## Build

From the repository root:

```bash
docker build -f docker/Dockerfile -t voxtral-stt-api:local .
```

### Building for a different CUDA version

The Dockerfile accepts build args to target CUDA 12.6, 12.7, or 12.8:

```bash
# CUDA 12.6
docker build -f docker/Dockerfile -t voxtral-stt-api:local \
  --build-arg CUDA_VERSION=12.6.3 \
  --build-arg TORCH_BACKEND=cu126 .

# CUDA 12.7
docker build -f docker/Dockerfile -t voxtral-stt-api:local \
  --build-arg CUDA_VERSION=12.7.1 \
  --build-arg TORCH_BACKEND=cu127 .

# CUDA 12.8 (default)
docker build -f docker/Dockerfile -t voxtral-stt-api:local .
```

| Build arg | Default | Description |
|-----------|---------|-------------|
| `CUDA_VERSION` | `12.8.0` | NVIDIA CUDA base image tag |
| `TORCH_BACKEND` | `cu128` | PyTorch wheel tag (`cu126`, `cu127`, `cu128`) |
| `PYTORCH_CUDA_INDEX_URL` | `https://download.pytorch.org/whl/${TORCH_BACKEND}` | PyTorch wheel index URL |

## Run

```bash
docker run --rm -it --gpus all -p 8000:8000 \
  -e VOXTRAL_API_KEY=secret_token \
  -e HF_TOKEN=hf_... \
  -e MAX_CONCURRENT_CONNECTIONS=100 \
  voxtral-stt-api:local
```

Endpoints:
- HTTP health: `http://localhost:8000/healthz`
- WebSocket: `ws://localhost:8000/api/asr-streaming`

Notes:
- The container image does not include the client scripts under `tests/`.
  Run warmup/bench from the host against the container.
