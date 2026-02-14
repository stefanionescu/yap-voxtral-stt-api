# Yap Voxtral STT API

Production-ready streaming speech-to-text server built on **Mistral Voxtral Realtime** and **vLLM**. Exposes a single WebSocket endpoint with a JSON envelope protocol, connection lifecycle enforcement, and internal segment rolling for unbounded ("infinite") audio streams. Ships with pinned dependencies, shell-based lifecycle scripts, and deterministic test/benchmark clients.

## Contents

- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Quickstart (GPU Server)](#quickstart-gpu-server)
- [WebSocket API (Overview)](#websocket-api-overview)
- [Docker](#docker)
- [Local Test Dependencies (CPU-only)](#local-test-dependencies-cpu-only)
- [Test Clients](#test-clients)
- [Stopping and Restarting](#stopping-and-restarting)
- [Linting](#linting)
- [Advanced Guide](#advanced-guide)

## Key Features

- **Real-time streaming transcription** over WebSocket with sub-second partial results.
- **Infinite audio streams** from a single connection — internal segment rolling handles arbitrarily long sessions transparently.
- **Automatic barge-in** — starting a new utterance cancels the previous one without reconnecting.
- **Connection lifecycle enforcement** — idle timeout, max duration, and a capacity guard prevent resource leaks.
- **Configurable transcription delay** — tune the model-inherent lookahead (`80ms`..`2400ms`) to trade latency for accuracy.
- **GPU-aware auto-tuning** — `max_num_seqs` and `max_num_batched_tokens` are selected per-GPU at startup. FP8 KV cache is enabled automatically on capable hardware.
- **Benchmark harness** — concurrency sweeps with p50/p95 summaries out of the box.

## Prerequisites

**Server (GPU host):**

- Linux with NVIDIA GPU (L40S recommended). A working CUDA 12.6+ driver stack.
- Python 3.11 (the launcher uses `python3.11` if available).
- [`uv`](https://docs.astral.sh/uv/) recommended (used for GPU-friendly installs and PyTorch wheel selection).

**Test clients (no GPU required):**

- Python 3.11+
- `ffmpeg` is optional (WAV decoding works without it; other audio formats may use it as a fallback).

## Quickstart (GPU Server)

Set the required environment variables:

```bash
export VOXTRAL_API_KEY="your-secret-key"  # required — authenticates every WebSocket connection
export HF_TOKEN="hf_..."                  # recommended — avoids rate limits on model download
```

Start the server:

```bash
bash scripts/main.sh
```

The launcher creates a venv at `.venv/`, installs pinned deps, starts uvicorn, polls `/healthz` until ready, then tails `server.log`. Ctrl+C detaches from the log tail only — the server keeps running.

For background deployments (skip log tailing):

```bash
TAIL_LOGS=0 bash scripts/main.sh
```

Verify the server is healthy:

```bash
curl -s http://localhost:8000/healthz
# {"status":"ok"}
```

You should see `{"status":"ok"}`. If the server is still loading the model, the health check will return a connection error — wait and retry.

See [ADVANCED.md](ADVANCED.md) for the full environment variable reference, vLLM tuning, and lifecycle script details.

## WebSocket API (Overview)

Connect with an API key (query parameter):

```
ws://server:8000/api/asr-streaming?api_key=YOUR_KEY
```

Every message is a JSON text frame with this envelope:

```json
{
  "type": "...",
  "session_id": "stable-user-id",
  "request_id": "utterance-id",
  "payload": {}
}
```

Transcribe audio in three steps:

```json
// 1. Start an utterance
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":false}}

// 2. Stream audio chunks (PCM16 LE, 16kHz, mono, base64-encoded)
{"type":"input_audio_buffer.append","session_id":"s1","request_id":"utt-1","payload":{"audio":"<base64>"}}

// 3. Finalize
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":true}}
```

The server streams back these frame types:

| Type | When |
|------|------|
| `session.created` | Connection established |
| `token` | Partial transcription word/fragment |
| `final` | Normalized full transcription for the utterance |
| `done` | Utterance complete (includes `usage`) |
| `status` | Server warnings (e.g. overload drops) |
| `error` | Validation or internal error |
| `pong` | Response to `ping` |
| `session_end` | Response to `end` (clean close) |
| `cancelled` | Response to `cancel` |

For the full protocol reference — authentication methods, close codes, error schema, cancellation, and session management — see [ADVANCED.md > API — WebSocket /api/asr-streaming](ADVANCED.md#api--websocket-apiasr-streaming).

## Docker

Build the image from the repository root:

```bash
docker build -f docker/Dockerfile -t voxtral-stt-api:local .
```

Run with GPU access:

```bash
docker run --rm -it --gpus all -p 8000:8000 \
  -e VOXTRAL_API_KEY=your-secret-key \
  -e HF_TOKEN=hf_... \
  voxtral-stt-api:local
```

Verify:

```bash
curl -s http://localhost:8000/healthz
```

The default image targets CUDA 12.8. To build for a different CUDA version, pass build args:

```bash
# CUDA 12.6
docker build -f docker/Dockerfile -t voxtral-stt-api:local \
  --build-arg CUDA_VERSION=12.6.3 \
  --build-arg TORCH_BACKEND=cu126 .

# CUDA 12.7
docker build -f docker/Dockerfile -t voxtral-stt-api:local \
  --build-arg CUDA_VERSION=12.7.1 \
  --build-arg TORCH_BACKEND=cu127 .
```

See [docker/README.md](docker/README.md) for the full build arg reference and runtime notes.

## Local Test Dependencies (CPU-only)

To run the test clients on a machine without a GPU:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -r requirements-local.txt
```

Then point any client at a running server:

```bash
export VOXTRAL_API_KEY="your-secret-key"
python -m tests.e2e.warmup --server localhost:8000
```

## Test Clients

All clients live under `tests/e2e/` and speak the WebSocket envelope protocol. Sample audio files are in `samples/`.

**Warmup** — single utterance with metrics (health check):

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.warmup --server localhost:8000
```

**Benchmark** — concurrent load generator with p50/p95 summaries:

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.bench --server localhost:8000 --n 64 --concurrency 64
```

**Idle timeout** — validates server closes idle connections:

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.idle --server localhost:8000
```

**Conversation** — two utterances over one WebSocket connection:

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.convo --server localhost:8000
```

**Remote** — warmup-equivalent for remote GPU deployments:

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.remote --server your-gpu-host:8000
```

For full flag reference and example commands, see [ADVANCED.md > Test Clients](ADVANCED.md#test-clients).

## Stopping and Restarting

Stop the server gracefully:

```bash
bash scripts/stop.sh
```

Restart (stop + start):

```bash
bash scripts/restart.sh
```

**Nuke mode** removes `.venv/`, `models/`, logs, and common caches under `~/.cache/` (HF/torch/vLLM/triton/uv/pip). This is irreversible and will force a full re-download and reinstall on the next start.

```bash
NUKE=1 bash scripts/stop.sh --nuke
```

The `NUKE=1` env var is a safety guard — the script refuses to nuke without it.

## Linting

Install dev dependencies and run the linter:

```bash
source scripts/lib/activate.sh
pip install -r requirements-dev.txt
bash scripts/lint.sh
```

Auto-fix where possible:

```bash
bash scripts/lint.sh --fix
```

Enable pre-commit hooks:

```bash
git config core.hooksPath .githooks
```

## Advanced Guide

[ADVANCED.md](ADVANCED.md) covers everything beyond quickstart:

- [Authentication coverage](ADVANCED.md#authentication-coverage) — which endpoints require an API key
- [CUDA version detection](ADVANCED.md#cuda-version) — auto-detection table and manual override
- [Model snapshot and tekken.json patching](ADVANCED.md#model-snapshot-and-tekkenjson-patching) — what happens at startup
- [Transcription delay tuning](ADVANCED.md#voxtral-realtime-latency-transcription_delay_ms) — the model-inherent lookahead and how to configure it
- [vLLM configuration](ADVANCED.md#vllm-configuration) — tunable knobs, auto-tuning behavior, GPU profiles
- [Full WebSocket protocol reference](ADVANCED.md#api--websocket-apiasr-streaming) — auth methods, close codes, message types, error schema, cancellation
- [Internal segment rolling](ADVANCED.md#internal-segment-rolling) — how infinite streaming works under the hood
- [Connection management patterns](ADVANCED.md#connection-management) — long-lived connections, keep-alive, scoping by request_id
- [Complete environment variable reference](ADVANCED.md#environment-variables) — every env var the server reads, organized by category
- [Troubleshooting](ADVANCED.md#troubleshooting) — symptom/cause/fix for common issues
