# Yap Voxtral STT API Advanced Guide

This guide covers advanced operations and deep-dive details for serving **Mistral Voxtral Realtime**
via **vLLM Realtime** behind a JSON WebSocket envelope.

See the main [README](README.md) for quickstart and basic usage.
See `.env.example` for a complete list of supported environment variables.

## Contents

- [Authentication Coverage](#authentication-coverage)
- [Model Snapshot and `tekken.json` Patching](#model-snapshot-and-tekkenjson-patching)
- [Voxtral Realtime Latency: `transcription_delay_ms`](#voxtral-realtime-latency-transcription_delay_ms)
- [vLLM Installation Notes](#vllm-installation-notes)
- [vLLM Configuration](#vllm-configuration)
- [Scripts and Lifecycle](#scripts-and-lifecycle)
- [API — WebSocket `/api/asr-streaming`](#api--websocket-apiasr-streaming)
- [Streaming Audio Details](#streaming-audio-details)
- [Connection Management](#connection-management)
- [Capacity and Latency Notes](#capacity-and-latency-notes)
- [Test Clients](#test-clients)
- [Troubleshooting](#troubleshooting)

## Authentication Coverage

- `GET /healthz` – No authentication required
- `GET /health` – No authentication required
- `GET /` – No authentication required
- `GET /api/asr-streaming` – **Requires** API key

## Model Snapshot and `tekken.json` Patching

Voxtral Realtime exposes a configuration value `transcription_delay_ms` inside `tekken.json`. This
repo patches that value **inside a writable local snapshot** of the model repo before starting vLLM.

Defaults:
- Snapshot directory: `models/voxtral` (`VOXTRAL_MODEL_DIR`)
- Model ID: `mistralai/Voxtral-Mini-4B-Realtime-2602` (`VOXTRAL_MODEL_ID`)

If the directory already contains:
- `params.json`
- `tekken.json`
- at least one `*.safetensors`

then the server treats it as “ready” and does not re-download on startup.

## Voxtral Realtime Latency: `transcription_delay_ms`

Voxtral Realtime is trained with an intentional transcription delay. Even with perfect scheduling,
time-to-first-delta and tail latency are bounded below by this configured delay.

Configure via:

```bash
export VOXTRAL_TRANSCRIPTION_DELAY_MS=400  # multiples of 80ms, 80..2400
```

Notes:
- This is **not** currently a per-request knob in vLLM’s Realtime protocol.
- The server applies the patch before vLLM engine initialization.
- If you need different delays per tenant, run multiple replicas (different `VOXTRAL_MODEL_DIR`).

## vLLM Installation Notes

This repo installs a pinned CUDA 12.8 stack via `scripts/main.sh`:

```bash
bash scripts/main.sh
```

Key points:
- Dependencies are pinned in `requirements.txt`.
- The launcher prefers `uv pip` and installs CUDA 12.8-compatible wheels (`--torch-backend=cu128`).
- The PyTorch CUDA wheel index used by the launcher is `https://download.pytorch.org/whl/cu128` (`PYTORCH_CUDA_INDEX_URL`).

Validation:

```bash
bash scripts/lib/doctor.sh
```

`scripts/lib/doctor.sh` fails unless `torch.version.cuda` is `12.x`.

## vLLM Configuration

Most vLLM knobs are env-driven and loaded at server startup (`src/runtime/settings.py`),
then passed into `AsyncEngineArgs` (`src/runtime/vllm.py`). A small set of values is
fixed/per-GPU to prevent accidental misconfiguration (e.g., Voxtral loader flags and
realtime batching defaults).

Common knobs:

| Variable | Default | Notes |
|---------|---------|------|
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.92` | Higher = more KV capacity, higher OOM risk |
| `VLLM_MAX_MODEL_LEN` | `1024` | Per-internal-segment context limit (audio+text). Smaller = more concurrency. |
| `VLLM_MAX_NUM_SEQS` | `128` | Upper bound on concurrent sequences in the scheduler |
| `VLLM_MAX_NUM_BATCHED_TOKENS` | `2048` / `4096` | Selected per-GPU at runtime (not env-configurable) |
| `VLLM_KV_CACHE_DTYPE` | `auto` | Default policy: auto-select `fp8` KV on FP8-capable GPUs (L40/L40S/H100/etc), else `auto` |
| `VLLM_CALCULATE_KV_SCALES` | `false` | Default policy: auto-enable when FP8 KV is selected (override via env) |
| `VLLM_ENFORCE_EAGER` | `false` | `true` is safer but usually slower |
| `VLLM_TOKENIZER_MODE` | `mistral` | Fixed in code (not configurable via env) |
| `VLLM_CONFIG_FORMAT` | `mistral` | Fixed in code (not configurable via env) |
| `VLLM_LOAD_FORMAT` | `mistral` | Fixed in code (not configurable via env) |

Auto-tuning behavior:
- If `VLLM_MAX_NUM_SEQS` is **unset**, the server estimates a safe `max_num_seqs` from GPU memory, model weight size,
  KV cache dtype, sliding window, and `VLLM_MAX_NUM_BATCHED_TOKENS`. Set `VLLM_MAX_NUM_SEQS` to disable tuning.
- `VLLM_MAX_NUM_BATCHED_TOKENS` is selected per-GPU in `src/runtime/gpu_profiles.py` (intentionally not configurable via env).

Voxtral streaming timing:
- Voxtral Realtime operates on an ~80ms step (12.5Hz). Approximate:
  - `segment_max_seconds ~= (VLLM_MAX_MODEL_LEN - headroom_tokens) * 0.08`
  - This repo supports long-running / “infinite” streaming by internally rolling segments
    (see `STT_INTERNAL_ROLL`, `STT_SEGMENT_SECONDS`, `STT_SEGMENT_OVERLAP_SECONDS`).

## Scripts and Lifecycle

This repo uses shell scripts to keep deployments repeatable.

- `scripts/main.sh` runs `scripts/steps/*` in order:
  - `01-require-env.sh` (validates required env vars)
  - `02-check-gpu.sh` (hard-fails unless GPU is on the allowlist)
  - `03-venv.sh` (creates `.venv/` if missing)
  - `04-install-deps.sh` (installs pinned deps; CUDA 12.8 torch backend)
  - `05-start-server.sh` (starts uvicorn detached; writes `server.pid`)
  - `06-wait-health.sh` (polls `/healthz`)
  - `07-tail-logs.sh` (tails `server.log` unless `TAIL_LOGS=0`)

Stop modes:

```bash
bash scripts/stop.sh
NUKE=1 bash scripts/stop.sh --nuke
```

The nuke mode is guarded by `NUKE=1` and removes:
- repo runtime state (`.venv/`, `models/`, logs)
- common caches under `~/.cache/` (HF/torch/vLLM/triton/uv/pip)

## API — WebSocket `/api/asr-streaming`

This server exposes a single WebSocket endpoint:

```text
ws://host:8000/api/asr-streaming
```

All client messages are JSON text frames with an envelope:

```json
{
  "type": "input_audio_buffer.append",
  "session_id": "stable-user-id",
  "request_id": "utterance-id",
  "payload": { "...": "..." }
}
```

### Authentication Methods

Provide the API key via:
- Query parameter: `?api_key=...`
- HTTP header: `X-API-Key: ...`

When auth fails, the server accepts the socket, sends a structured `error`, then closes with code `4001`.

### Connection Lifecycle

Server policy:
- Idle timeout: `WS_IDLE_TIMEOUT_S` (default: 150s; set to `0` to disable) closed with code `4000`
- Max duration: `WS_MAX_CONNECTION_DURATION_S` (default: 5400s = 90 min; set to `0` to disable) closed with code `4003`
- Capacity guard: `MAX_CONCURRENT_CONNECTIONS` (default: `0` = auto from tuned vLLM `max_num_seqs`) rejects with code `4002`

What counts as activity:
- Any received JSON text message (including `{"type":"ping",...}`)

This server does not currently treat WebSocket protocol-level Ping/Pong frames as activity.

### Close Codes

| Code | Meaning |
|------|---------|
| `1000` | Client-requested end (`type:"end"`) |
| `4000` | Idle timeout |
| `4001` | Unauthorized (bad/missing API key) |
| `4002` | Server at capacity |
| `4003` | Max connection duration reached |

### Messages You Send

Control:

```json
{"type":"ping","session_id":"s1","request_id":"r1","payload":{}}
{"type":"end","session_id":"s1","request_id":"r2","payload":{}}
{"type":"cancel","session_id":"s1","request_id":"r3","payload":{"reason":"client_request"}}
```

Session selection (optional):

```json
{"type":"session.update","session_id":"s1","request_id":"r1","payload":{"model":"mistralai/Voxtral-Mini-4B-Realtime-2602"}}
```

Only the configured model is allowed. Any other value is rejected with an `error`.

Transcription:

1. Start an utterance:

```json
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":false}}
```

2. Stream audio chunks (PCM16 16kHz mono, base64):

```json
{"type":"input_audio_buffer.append","session_id":"s1","request_id":"utt-1","payload":{"audio":"<base64 pcm16>"}} 
```

3. Finalize:

```json
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":true}}
```

### What You Receive

The server emits YAP-like streaming frames inside the envelope. You will typically see:
- `session.created`, `session.updated`
- `token` (payload contains `text`)
- `final` (payload contains `normalized_text`)
- `done` (payload contains `usage`)
- `status` (server warnings, e.g. overload drops)
- `error`

The server also emits:
- `pong` (in response to `ping`)
- `session_end` (in response to `end`)
- `cancelled` (in response to `cancel`)

### Cancellation and “Barge-in”

- `type:"cancel"` cancels any in-flight transcription and drains queued audio.
- Starting a new utterance (`commit final=false`) while another request is active on the same socket
  cancels the previous request automatically.

### Rate Limits

Rate limits are rolling-window counters per connection:

| Variable | Default | Applies To |
|---------|---------|------------|
| `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS` | `5000 / 60` | all message types except `ping/pong/end` |
| `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS` | `50 / 60` | `type:"cancel"` |

Important:
- STT streaming can easily exceed the default message limit depending on your chunk size.
- For 80ms audio chunks, you send ~750 `append` messages per minute.
- If you use 20ms chunks, it is ~3000 messages per minute.

If you stream audio, tune `WS_MAX_MESSAGES_PER_WINDOW` accordingly or you will be rate-limited.

### Error Payload Schema

All server-side errors are returned as:

```json
{
  "type": "error",
  "session_id": "s1",
  "request_id": "utt-1",
  "payload": {
    "code": "rate_limited",
    "message": "message rate limit: ...",
    "details": { "reason_code": "message_rate_limited" }
  }
}
```

## Streaming Audio Details

Expected audio format:
- PCM16 little-endian
- 16kHz sample rate
- mono
- base64-encoded inside `payload.audio`

Client recommendations:
- Chunk size: 80ms is a good default for Voxtral Realtime (matches its 80ms step).
- Use VAD on the client (or upstream) and send `commit final=true` when speech ends.
- Close the socket after `done` if you want to minimize KV/cache residency.

## Connection Management

This server supports long-lived WebSocket connections (hours/days) with many utterances per connection:
- Each utterance is scoped by `request_id`.
- Finalize quickly (`commit final=true`) and start a new `request_id` for the next utterance.
- You may keep the socket open across utterances; send `{"type":"ping",...}` periodically (or set `WS_IDLE_TIMEOUT_S=0`).

This server supports long-running / "infinite" speech on a single utterance by internally
rolling the active request into bounded vLLM segments (with a small audio overlap).

To stay live under overload, the server may drop oldest unprocessed audio once per-connection
backlog exceeds `STT_MAX_BACKLOG_SECONDS` (emits a `status` warning frame).

## Capacity and Latency Notes

Two latency components matter:
- Model-inherent delay: `VOXTRAL_TRANSCRIPTION_DELAY_MS` (80..2400ms, multiples of 80ms)
- System overhead: batching/scheduling, GPU contention, network buffering

Concurrency is often limited by KV-cache memory for long-lived streams. Practical levers:
- Keep sessions short and finalize quickly.
- Consider KV cache compression (`VLLM_KV_CACHE_DTYPE=fp8_*`) if supported by your vLLM build.
- If you need to change batching (`VLLM_MAX_NUM_BATCHED_TOKENS`), edit the per-GPU table in `src/runtime/gpu_profiles.py`.

## Test Clients

All clients speak the same `/api/asr-streaming` envelope protocol.

Warmup:

```bash
VOXTRAL_API_KEY=secret_token python -m tests.e2e.warmup --server localhost:8000 --file mid.wav
```

Benchmark:

```bash
VOXTRAL_API_KEY=secret_token python -m tests.e2e.bench --server localhost:8000 --n 100 --concurrency 100 --file mid.wav
```

Idle timeout:

```bash
VOXTRAL_API_KEY=secret_token python -m tests.e2e.idle --server localhost:8000
```

Conversation (two utterances over one connection):

```bash
VOXTRAL_API_KEY=secret_token python -m tests.e2e.convo --server localhost:8000
```

Remote client:

```bash
VOXTRAL_API_KEY=secret_token python -m tests.e2e.remote --server localhost:8000
```

## Troubleshooting

### vLLM Install Fails

- Confirm you are using `uv` on a GPU host.
- If you see PyTorch/CUDA mismatches, verify you are installing with `--torch-backend=cu128` (see `scripts/steps/04-install-deps.sh`).
- Run `bash scripts/lib/doctor.sh` to confirm `torch.version.cuda` is `12.x`.

### Model Download Is Slow or Fails

- Set `HF_TOKEN` to avoid rate limits and to access gated/private repos.
- Ensure the snapshot directory (`models/voxtral` by default) is writable.

### No `token` Events

- If you stream silence, you will usually get only the final.
- Remember the model runs with a configured `transcription_delay_ms` which can delay partial output.

### Rate Limited While Streaming

- Increase `WS_MAX_MESSAGES_PER_WINDOW` to match your chunk size.
- For 80ms chunks, use a value >= 800 per minute (plus headroom).
- For 20ms chunks, use a value >= 3200 per minute.
- For 10ms chunks, use a value >= 6500 per minute.

### Inbound Queue Full

If the server closes with an `error` reason code `inbound_queue_full`, the per-connection inbound
queue was saturated (`WS_INBOUND_QUEUE_MAX`).

Typical fixes:
- Use 80ms chunks (default client chunk size) instead of very small chunks.
- Reduce per-connection message rate (e.g. pack multiple frames per message if your client supports it).
- Increase `WS_INBOUND_QUEUE_MAX` conservatively (too high can increase memory use and tail latency).
