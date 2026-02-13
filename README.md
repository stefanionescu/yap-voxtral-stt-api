# Yap Voxtral STT API

Streaming speech-to-text (STT) server for **Mistral Voxtral Realtime** using **vLLM Realtime**.

- Default model: `mistralai/Voxtral-Mini-4B-Realtime-2602` (override with `VOXTRAL_MODEL_ID`)

- FastAPI + WebSocket endpoint: `GET /api/asr-streaming`
- JSON envelope: `{type, session_id, request_id, payload}`
- vLLM Realtime semantics inside the envelope (`session.update`, `input_audio_buffer.*`, `transcription.*`)
- API key auth, connection cap, idle timeout, hard max duration, rate limits
- Test clients + benchmarks (warmup, bench, idle, convo, remote)

This repo uses pinned dependencies, scripts for lifecycle management, and deterministic
test/benchmark clients.

## Contents

- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Quickstart (GPU Server)](#quickstart-gpu-server)
- [Health Check](#health-check)
- [WebSocket API (Overview)](#websocket-api-overview)
- [Local Test Dependencies (CPU-only)](#local-test-dependencies-cpu-only)
- [Test Clients](#test-clients)
- [Stopping and Restarting](#stopping-and-restarting)
- [Linting](#linting)
- [Docker](#docker)
- [Advanced Guide](#advanced-guide)

## Key Features

- vLLM Realtime-native Voxtral serving (no custom decoding loop).
- Envelope protocol for easy integration with existing clients.
- Strong connection lifecycle enforcement: idle timeout (150s), max duration (90 minutes), and a capacity guard (`MAX_CONCURRENT_CONNECTIONS`).
- Model-inherent “lookahead” latency is configurable via `VOXTRAL_TRANSCRIPTION_DELAY_MS` (patched into `tekken.json`).
- Receive/compute decoupling for steady streaming: inbound client messages are buffered in a bounded queue per connection.
- Bench harness for concurrency sweeps (8 / 32 / 64 / 100).

## Prerequisites

For running the server:
- Linux NVIDIA GPU host (L40S recommended) with a working CUDA driver stack.
- CUDA 13 runtime for the Python stack (the launcher installs cu130 wheels).
- Python 3.11 recommended (the scripts will use `python3.11` if available).
- `uv` recommended (used for GPU-friendly installs and PyTorch wheel selection).

For running test clients (no GPU required):
- Python 3.11+
- `ffmpeg` is optional (WAV decoding works without it; other formats may use it as a fallback).

## Quickstart (GPU Server)

Set required environment variables:

```bash
export VOXTRAL_API_KEY="secret_token"       # required for every websocket connection
export MAX_CONCURRENT_CONNECTIONS=100       # optional (default: 100)
export HF_TOKEN="hf_your_token"             # recommended for model downloads
```

See `.env.example` for the full list of supported environment variables.

Optional but recommended knobs:

```bash
export VOXTRAL_TRANSCRIPTION_DELAY_MS=400   # multiples of 80ms (80..2400)
export WS_MAX_CONNECTION_DURATION_S=5400    # default: 90 minutes
export WS_IDLE_TIMEOUT_S=150               # default: 150 seconds
export WS_INBOUND_QUEUE_MAX=256            # bounded per-connection inbound queue
```

Start the server:

```bash
bash scripts/main.sh
```

Notes:
- `scripts/main.sh` creates a venv at `.venv`, installs pinned deps from `requirements.txt`,
  and tails `server.log`.
- Ctrl+C detaches from the log tail only. Stop the server with `bash scripts/stop.sh`.
- Logs: `tail -f server.log`
- Status: `bash scripts/lib/status.sh`
- Bind/port: set `SERVER_BIND_HOST` / `SERVER_PORT` (defaults: `0.0.0.0:8000`)

Start without tailing logs (recommended for background deployments):

```bash
TAIL_LOGS=0 bash scripts/main.sh
```

## Health Check

```bash
curl -s http://localhost:8000/healthz
```

## WebSocket API (Overview)

Connect (query parameter auth):

```text
ws://server:8000/api/asr-streaming?api_key=VOXTRAL_API_KEY
```

All messages are JSON text frames with this envelope:

```json
{
  "type": "...",
  "session_id": "stable-user-id",
  "request_id": "utterance-id",
  "payload": {}
}
```

Minimal transcription flow:

```json
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":false}}
{"type":"input_audio_buffer.append","session_id":"s1","request_id":"utt-1","payload":{"audio":"<base64 pcm16 16k mono>"}} 
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":true}}
```

The server forwards vLLM Realtime events (same `type` values) inside the envelope, for example:
- `session.created`, `session.updated`
- `transcription.delta` (payload has `delta`)
- `transcription.done` (payload has `text`)
- `error`

Full protocol details (close codes, error payload schema, lifecycle rules) are in `ADVANCED.md`.

## Local Test Dependencies (CPU-only)

To run the Python test clients on a laptop without installing vLLM/GPU wheels:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -r requirements-local.txt
```

Then point clients at a running server:

```bash
export VOXTRAL_API_KEY="secret_token"
python tests/warmup.py --server localhost:8000
```

## Test Clients

All runnable client scripts live under `tests/`:

- Sample audio lives under `samples/`.
- `tests/warmup.py` – one utterance (default: `samples/mid.wav`) + metrics.
- `tests/bench.py` – concurrent load generator with p50/p95 summaries.
- `tests/idle.py` – validates idle timeout close behavior (default: code `4000`).
- `tests/convo.py` – two utterances over one WebSocket connection.
- `tests/remote.py` – warmup-equivalent client for remote GPU deployments.

Examples:

```bash
VOXTRAL_API_KEY=secret_token python tests/warmup.py --server localhost:8000
VOXTRAL_API_KEY=secret_token python tests/bench.py --server localhost:8000 --n 64 --concurrency 64
VOXTRAL_API_KEY=secret_token python tests/idle.py --server localhost:8000
VOXTRAL_API_KEY=secret_token python tests/convo.py --server localhost:8000
VOXTRAL_API_KEY=secret_token python tests/remote.py --server localhost:8000
```

## Stopping and Restarting

```bash
bash scripts/stop.sh
bash scripts/restart.sh
```

Nuke (wipes `.venv/`, `models/`, logs, and common caches under `~/.cache/`):

```bash
NUKE=1 bash scripts/stop.sh --nuke
```

## Linting

```bash
source scripts/lib/activate.sh
pip install -r requirements-dev.txt
bash scripts/lint.sh
bash scripts/lint.sh --fix
```

Enable git hooks:

```bash
git config core.hooksPath .githooks
```

## Docker

This repo ships Docker scaffolding but does not publish images.

- `docker/Dockerfile`
- `docker/README.md`

## Advanced Guide

See `ADVANCED.md`.
