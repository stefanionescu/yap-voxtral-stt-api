# Yap Voxtral STT API Advanced Guide

This guide covers advanced operations and deep-dive details for serving **Mistral Voxtral Realtime**
via **vLLM Realtime** behind a JSON WebSocket envelope.

See the main [README](README.md) for quickstart and basic usage.

## Contents

- [Authentication Coverage](#authentication-coverage)
- [Model Snapshot and `tekken.json` Patching](#model-snapshot-and-tekkenjson-patching)
- [Voxtral Realtime Latency: `transcription_delay_ms`](#voxtral-realtime-latency-transcription_delay_ms)
- [vLLM Installation Notes](#vllm-installation-notes)
- [vLLM Configuration](#vllm-configuration)
- [API — WebSocket `/ws`](#api--websocket-ws)
- [Streaming Audio Details](#streaming-audio-details)
- [Connection Management](#connection-management)
- [Capacity and Latency Notes](#capacity-and-latency-notes)
- [Test Clients](#test-clients)
- [Troubleshooting](#troubleshooting)

## Authentication Coverage

- `GET /healthz` – No authentication required
- `GET /health` – No authentication required
- `GET /` – No authentication required
- `GET /ws` – **Requires** API key

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

This repo pins `vllm==...` in `requirements.txt` but expects GPU hosts to install using vLLM’s
nightly wheel index. `scripts/main.sh` does this automatically when `uv` is available:

```bash
VLLM_WHEELS_INDEX_URL=https://wheels.vllm.ai/nightly/cu130 bash scripts/main.sh
```

Key points:
- The launcher prefers `uv pip` and installs cu130 wheels (`--torch-backend=cu130`).
- If `uv` is not installed, the script falls back to `pip`. In that case you may need to install a
  compatible CUDA `torch` wheel manually.

## vLLM Configuration

All vLLM knobs are env-driven (`src/config/vllm.py`) and then passed into `AsyncEngineArgs`
(`src/runtime/vllm_engine.py`).

Common knobs:

| Variable | Default | Notes |
|---------|---------|------|
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.92` | Higher = more KV capacity, higher OOM risk |
| `VLLM_MAX_MODEL_LEN` | `67500` | ~= 90 minutes at ~80ms/token |
| `VLLM_MAX_NUM_SEQS` | `128` | Upper bound on concurrent sequences in the scheduler |
| `VLLM_MAX_NUM_BATCHED_TOKENS` | `4096` | Higher = throughput, worse tail latency under load |
| `VLLM_KV_CACHE_DTYPE` | `auto` | FP8 variants can reduce KV memory on L40S/H100 (vLLM-dependent) |
| `VLLM_ENFORCE_EAGER` | `false` | `true` is safer but usually slower |
| `VLLM_TOKENIZER_MODE` | `mistral` | Voxtral-recommended loader flag |
| `VLLM_CONFIG_FORMAT` | `mistral` | Voxtral-recommended loader flag |
| `VLLM_LOAD_FORMAT` | `mistral` | Voxtral-recommended loader flag |

Voxtral streaming timing:
- Voxtral Realtime operates on an ~80ms step (12.5Hz). Approximate:
  - `max_seconds ~= VLLM_MAX_MODEL_LEN * 0.08`
  - `VLLM_MAX_MODEL_LEN ~= max_seconds / 0.08`

## API — WebSocket `/ws`

This server exposes a single WebSocket endpoint:

```text
ws://host:8000/ws
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
- Idle timeout: `WS_IDLE_TIMEOUT_S` (default: 150s) closed with code `4000`
- Max duration: `WS_MAX_CONNECTION_DURATION_S` (default: 5400s = 90 min) closed with code `4003`
- Capacity guard: `MAX_CONCURRENT_CONNECTIONS` (required) rejects with code `4002`

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

The server forwards vLLM Realtime events inside the envelope. You will typically see:
- `session.created`, `session.updated`
- `transcription.delta` (payload contains `delta`)
- `transcription.done` (payload contains `text`)
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
    "reason_code": "message_rate_limited",
    "details": { }
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
- Close the socket after `transcription.done` if you want to minimize KV/cache residency.

## Connection Management

This server is designed for “voice agent” usage where sessions are utterance-scoped:
- Keep the socket open while a user is talking.
- Finalize quickly (`commit final=true`).
- Close the socket after you receive `transcription.done`.

Long-running meeting-style sessions are possible but will reduce achievable concurrency on a single GPU.

## Capacity and Latency Notes

Two latency components matter:
- Model-inherent delay: `VOXTRAL_TRANSCRIPTION_DELAY_MS` (80..2400ms, multiples of 80ms)
- System overhead: batching/scheduling, GPU contention, network buffering

Concurrency is often limited by KV-cache memory for long-lived streams. Practical levers:
- Keep sessions short and finalize quickly.
- Consider KV cache compression (`VLLM_KV_CACHE_DTYPE=fp8_*`) if supported by your vLLM build.
- Tune batching (`VLLM_MAX_NUM_BATCHED_TOKENS`) to balance throughput vs tail latency.

## Test Clients

All clients speak the same `/ws` envelope protocol.

Warmup:

```bash
VOXTRAL_API_KEY=secret_token python tests/warmup.py --server localhost:8000 --file mid.wav
```

Benchmark:

```bash
VOXTRAL_API_KEY=secret_token python tests/bench.py --server localhost:8000 --n 100 --concurrency 100 --file mid.wav
```

Idle timeout:

```bash
VOXTRAL_API_KEY=secret_token python tests/idle.py --server localhost:8000
```

Conversation (two utterances over one connection):

```bash
VOXTRAL_API_KEY=secret_token python tests/convo.py --server localhost:8000
```

Remote client:

```bash
VOXTRAL_API_KEY=secret_token python tests/remote.py --server localhost:8000
```

## Troubleshooting

### vLLM Install Fails

- Confirm you are using `uv` on a GPU host.
- Ensure `VLLM_WHEELS_INDEX_URL` points to the cu130 wheel index (`https://wheels.vllm.ai/nightly/cu130`).
- If you see PyTorch/CUDA mismatches, verify you are installing with `--torch-backend=cu130` (see `scripts/main.sh`).

### Model Download Is Slow or Fails

- Set `HF_TOKEN` to avoid rate limits and to access gated/private repos.
- Ensure the snapshot directory (`models/voxtral` by default) is writable.

### No `transcription.delta` Events

- If you stream silence, you will usually get only the final.
- Remember the model runs with a configured `transcription_delay_ms` which can delay partial output.

### Rate Limited While Streaming

- Increase `WS_MAX_MESSAGES_PER_WINDOW` to match your chunk size.
- For 80ms chunks, use a value >= 800 per minute (plus headroom).
- For 20ms chunks, use a value >= 3200 per minute.
- For 10ms chunks, use a value >= 6500 per minute.
