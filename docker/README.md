# Docker

This repository includes Docker scaffolding for running the server in a container.
It does not publish prebuilt images.

The image runs:
- CUDA 13 runtime base (`nvidia/cuda:13.0.0-runtime-ubuntu22.04`)
- Python 3.11
- Pinned Python deps from `requirements.txt`

## Build

From the repository root:

```bash
docker build -f docker/Dockerfile -t voxtral-stt-api:local .
```

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
