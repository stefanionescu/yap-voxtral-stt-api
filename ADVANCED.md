# Yap Voxtral STT API Advanced Guide

Operational depth, configuration reference, and protocol details for the Voxtral STT server. Start with the [README](README.md) for quickstart and basic usage.

## Contents

- [Authentication Coverage](#authentication-coverage)
- [CUDA Version](#cuda-version)
- [Model Snapshot and tekken.json Patching](#model-snapshot-and-tekkenjson-patching)
- [Voxtral Realtime Latency: transcription_delay_ms](#voxtral-realtime-latency-transcription_delay_ms)
- [vLLM Installation Notes](#vllm-installation-notes)
- [vLLM Configuration](#vllm-configuration)
- [Scripts and Lifecycle](#scripts-and-lifecycle)
- [API — WebSocket /api/asr-streaming](#api--websocket-apiasr-streaming)
- [Streaming Audio Details](#streaming-audio-details)
- [Internal Segment Rolling](#internal-segment-rolling)
- [Connection Management](#connection-management)
- [Capacity and Latency Notes](#capacity-and-latency-notes)
- [GPU Profiles](#gpu-profiles)
- [Test Clients](#test-clients)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Authentication Coverage

| Endpoint | Auth Required |
|----------|---------------|
| `GET /` | No |
| `GET /health` | No |
| `GET /healthz` | No |
| `GET /api/asr-streaming` (WebSocket) | Yes — API key via query param or header |

## CUDA Version

The launcher auto-detects the installed CUDA toolkit version from `nvidia-smi` (falling back to `nvcc`) and selects the matching PyTorch wheel tag:

| Detected CUDA | `TORCH_BACKEND` | `PYTORCH_CUDA_INDEX_URL` |
|---------------|-----------------|--------------------------|
| 12.6 | `cu126` | `https://download.pytorch.org/whl/cu126` |
| 12.7 | `cu127` | `https://download.pytorch.org/whl/cu127` |
| 12.8+ | `cu128` | `https://download.pytorch.org/whl/cu128` |

To override auto-detection, set both env vars before starting:

```bash
export TORCH_BACKEND=cu126
export PYTORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu126
bash scripts/main.sh
```

When both are set, auto-detection is skipped entirely. The detection logic lives in `scripts/lib/cuda.sh`.

Validate your CUDA stack after install:

```bash
bash scripts/lib/doctor.sh
```

This fails unless `torch.version.cuda` reports `12.x`.

## Model Snapshot and tekken.json Patching

At startup the server creates a writable local snapshot of the Hugging Face model repo, then patches `tekken.json` inside it to set `transcription_delay_ms`.

Defaults:
- Model ID: `mistralai/Voxtral-Mini-4B-Realtime-2602` (`VOXTRAL_MODEL_ID`)
- Snapshot directory: `models/voxtral` (`VOXTRAL_MODEL_DIR`)

The server considers a snapshot "ready" and skips re-download when the directory already contains `params.json`, `tekken.json`, and at least one `*.safetensors` file.

To force a fresh download, delete the snapshot directory (or use nuke mode).

## Voxtral Realtime Latency: transcription_delay_ms

Voxtral Realtime is trained with an intentional transcription delay. Even with perfect scheduling, time-to-first-token and tail latency are bounded below by this value. Lower values mean faster partial results but may reduce transcription accuracy.

```bash
export VOXTRAL_TRANSCRIPTION_DELAY_MS=400  # multiples of 80ms, range 80..2400
```

The server applies the patch to `tekken.json` before vLLM engine initialization. This is **not** a per-request knob — it is baked into the model snapshot at startup.

If you need different delays per tenant, run multiple replicas with different `VOXTRAL_MODEL_DIR` values (each snapshot gets its own patched `tekken.json`).

## vLLM Installation Notes

`scripts/main.sh` handles the full install:

1. Creates a venv at `.venv/` if it doesn't exist.
2. Auto-detects CUDA version and selects matching PyTorch wheels (see [CUDA Version](#cuda-version)).
3. Installs pinned dependencies from `requirements.txt` via `uv pip` with `--torch-backend=${TORCH_BACKEND}`.

Dependencies are pinned. The launcher prefers `uv` for reproducible GPU-aware installs.

Validate the resulting environment:

```bash
bash scripts/lib/doctor.sh
```

## vLLM Configuration

vLLM knobs are env-driven and loaded at server startup (`src/runtime/settings.py`), then passed into `AsyncEngineArgs` (`src/runtime/vllm.py`).

### Tunable Knobs

| Variable | Default | Notes |
|----------|---------|-------|
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.92` | Fraction of GPU memory for KV cache. Higher = more capacity, higher OOM risk. |
| `VLLM_MAX_MODEL_LEN` | `1024` | Per-internal-segment context limit (audio+text tokens). Smaller = more concurrency. |
| `VLLM_MAX_NUM_SEQS` | `128` | Upper bound on concurrent sequences. Unset to enable auto-tuning. |
| `VLLM_ENFORCE_EAGER` | `false` | Disable CUDA graphs. Safer but usually slower. |
| `VLLM_KV_CACHE_DTYPE` | `auto` | Auto-selects `fp8` on FP8-capable GPUs (Ada/Hopper, compute capability >= 8.9). |
| `VLLM_CALCULATE_KV_SCALES` | `false` | Auto-enabled when FP8 KV is selected. Override via env. |
| `VLLM_DTYPE` | `bfloat16` | Model dtype for vLLM. |
| `VLLM_COMPILATION_CONFIG` | `{"cudagraph_mode":"PIECEWISE"}` | JSON dict for vLLM compilation config. Set to `null` to disable. |
| `VLLM_DISABLE_COMPILE_CACHE` | `true` | Disable the vLLM compile cache. |

### Fixed Values (Not Configurable)

These are hardcoded to prevent misconfiguration with Voxtral's Mistral-format weights:

| Setting | Value |
|---------|-------|
| `tokenizer_mode` | `mistral` |
| `config_format` | `mistral` |
| `load_format` | `mistral` |
| `max_num_batched_tokens` | Per-GPU (see [GPU Profiles](#gpu-profiles)) |

### Auto-Tuning Behavior

When `VLLM_MAX_NUM_SEQS` is **unset**, the server estimates a safe value from:
- Total GPU memory (via `nvidia-smi`)
- Model weight size (sum of `*.safetensors` files)
- KV cache dtype and bytes-per-element
- GQA parameters from `params.json` (`n_kv_heads`, `head_dim`, `sliding_window`)
- `VLLM_MAX_MODEL_LEN` and `max_num_batched_tokens`
- A 90% KV budget fraction (10% headroom for weights, activations, fragmentation)

The estimate is capped at 512. Set `VLLM_MAX_NUM_SEQS` explicitly to disable tuning.

`max_num_batched_tokens` is selected per-GPU in `src/runtime/gpu_profiles.py` and is intentionally not exposed as an env var to avoid throughput/latency footguns.

### Voxtral Streaming Timing

Voxtral Realtime operates on an ~80ms step (12.5 Hz). Approximate segment capacity:

```
segment_max_seconds ~= (VLLM_MAX_MODEL_LEN - 128 headroom tokens) * 0.08
```

With the default `VLLM_MAX_MODEL_LEN=1024`, that is roughly `(1024 - 128) * 0.08 = ~71.7s` per internal segment. The server handles longer audio transparently via [internal segment rolling](#internal-segment-rolling).

## Scripts and Lifecycle

`scripts/main.sh` runs steps in order:

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `01-require-env.sh` | Validates required env vars |
| 2 | `02-check-gpu.sh` | Hard-fails unless GPU is on the allowlist |
| 3 | `03-venv.sh` | Creates `.venv/` if missing |
| 4 | `04-install-deps.sh` | Installs pinned deps (CUDA-aware PyTorch wheels) |
| 5 | `05-start-server.sh` | Starts uvicorn detached; writes `server.pid` |
| 6 | `06-wait-health.sh` | Polls `/healthz` (timeout: 600s default) |
| 7 | `07-tail-logs.sh` | Tails `server.log` unless `TAIL_LOGS=0` |

Useful operational commands:

```bash
tail -F server.log              # follow server logs
bash scripts/lib/status.sh      # check if the server is running
bash scripts/lib/doctor.sh      # validate CUDA/torch environment
```

Logs are bounded — a trimmer runs periodically (see `scripts/config/logs.sh`).

### Stop Modes

Graceful stop kills the server and launcher processes:

```bash
bash scripts/stop.sh
```

**Warning: nuke mode is destructive and irreversible.** It removes `.venv/`, `models/`, logs, and common caches under `~/.cache/` (HF, torch, vLLM, triton, uv, pip). The next start will re-download everything.

```bash
NUKE=1 bash scripts/stop.sh --nuke
```

The `NUKE=1` env var and `--nuke` flag are both required — the script refuses to nuke without the env guard.

## API — WebSocket /api/asr-streaming

Single WebSocket endpoint:

```
ws://host:8000/api/asr-streaming
```

All client and server messages are JSON text frames with an envelope:

```json
{
  "type": "...",
  "session_id": "stable-user-id",
  "request_id": "utterance-id",
  "payload": {}
}
```

### Authentication Methods

Provide the API key (`VOXTRAL_API_KEY`) via either method:

Query parameter:

```
ws://host:8000/api/asr-streaming?api_key=YOUR_KEY
```

HTTP header:

```
X-API-Key: YOUR_KEY
```

On auth failure, the server accepts the WebSocket, sends a structured `error` frame, then closes with code `1008`. This accept-then-close pattern ensures clients always receive a machine-readable error rather than an opaque rejection.

### Connection Lifecycle

| Policy | Variable | Default | Close Code |
|--------|----------|---------|------------|
| Idle timeout | `WS_IDLE_TIMEOUT_S` | `150` (seconds) | `4000` |
| Max duration | `WS_MAX_CONNECTION_DURATION_S` | `5400` (90 min) | `4003` |
| Capacity guard | `MAX_CONCURRENT_CONNECTIONS` | `0` (auto from `max_num_seqs`) | `1013` |

Set any timeout to `0` to disable it.

**What counts as activity:** any received JSON text message (including `{"type":"ping",...}`). WebSocket protocol-level Ping/Pong frames are **not** counted as activity — use application-level `ping` messages to keep connections alive.

The idle timeout watchdog does not close a connection while an utterance is in-flight (i.e., between `commit final=false` and `done`).

### Close Codes

| Code | Meaning |
|------|---------|
| `1000` | Client-requested end (`type:"end"`) |
| `1008` | Unauthorized (bad/missing API key) |
| `1013` | Server at capacity |
| `4000` | Idle timeout |
| `4003` | Max connection duration reached |

The close codes for unauthorized (`WS_CLOSE_UNAUTHORIZED_CODE`) and at-capacity (`WS_CLOSE_BUSY_CODE`) are configurable via env vars.

### Messages You Send

**Control messages:**

```json
{"type":"ping","session_id":"s1","request_id":"r1","payload":{}}
{"type":"end","session_id":"s1","request_id":"r1","payload":{}}
{"type":"cancel","session_id":"s1","request_id":"r1","payload":{"reason":"client_request"}}
```

- `ping` — server responds with `pong`. Resets the idle timer.
- `end` — server responds with `session_end`, then closes with code `1000`.
- `cancel` — cancels in-flight transcription and drains queued audio. Server responds with `cancelled`.

**Session selection (optional):**

```json
{"type":"session.update","session_id":"s1","request_id":"r1","payload":{"model":"mistralai/Voxtral-Mini-4B-Realtime-2602"}}
```

Only the configured model is accepted. Any other value is rejected with an `error` (`reason_code: "unsupported_model"`).

**Transcription flow (3 steps):**

1. Start an utterance:

```json
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":false}}
```

2. Stream audio chunks:

```json
{"type":"input_audio_buffer.append","session_id":"s1","request_id":"utt-1","payload":{"audio":"<base64 PCM16 16kHz mono>"}}
```

3. Finalize the utterance:

```json
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":true}}
```

The `request_id` on `append` and final `commit` must match the `request_id` from the initial `commit`. Mismatches are rejected with `reason_code: "request_id_mismatch"`.

### What You Receive

| Type | Payload | When |
|------|---------|------|
| `session.created` | — | After connection + first `session.update` |
| `session.updated` | — | After explicit `session.update` |
| `token` | `{"text": "..."}` | Partial transcription (streaming) |
| `final` | `{"normalized_text": "..."}` | Complete transcription for the utterance |
| `done` | `{"usage": {...}}` | Utterance processing complete |
| `status` | `{"kind": "overload_drop", ...}` | Server warnings (e.g. audio dropped under overload) |
| `error` | `{"code": "...", "message": "...", "details": {...}}` | Validation or internal error |
| `pong` | `{}` | Response to `ping` |
| `session_end` | `{}` | Response to `end` |
| `cancelled` | `{"reason": "..."}` | Response to `cancel` |

### Cancellation and Barge-In

**Explicit cancel:** send `{"type":"cancel",...}` to cancel any in-flight transcription and drain queued audio.

**Automatic barge-in:** starting a new utterance (`commit final=false`) while another request is active on the same connection cancels the previous request automatically. No explicit `cancel` needed.

### Error Payload Schema

All errors follow this structure:

```json
{
  "type": "error",
  "session_id": "s1",
  "request_id": "utt-1",
  "payload": {
    "code": "invalid_message",
    "message": "human-readable description",
    "details": {
      "reason_code": "invalid_message"
    }
  }
}
```

Error codes emitted by the server:

| `payload.code` | When |
|-----------------|------|
| `authentication_failed` | Bad or missing API key |
| `server_at_capacity` | Connection limit reached |
| `invalid_message` | Unparseable JSON or unknown message type |
| `invalid_payload` | Missing/malformed fields (e.g. no `audio`, wrong model, mismatched `request_id`) |
| `internal_error` | Server-side failure (e.g. inbound queue full) |

## Streaming Audio Details

Expected audio format:

- **Encoding:** PCM16 little-endian
- **Sample rate:** 16kHz
- **Channels:** mono
- **Transport:** base64-encoded inside `payload.audio`

Each audio "token" in Voxtral Realtime represents ~80ms (2,560 bytes of raw PCM16 at 16kHz).

### Client Recommendations

- **Chunk size:** 80ms is a good default — it matches Voxtral's internal step. Larger chunks work fine; very small chunks may saturate the inbound queue.
- **VAD:** use voice activity detection on the client (or upstream) and send `commit final=true` when speech ends. This lets the server finalize quickly and frees KV cache capacity.
- **Socket lifecycle:** close the socket after `done` if you only need single-shot transcription. For multi-utterance sessions, keep the socket open and reuse it with fresh `request_id` values.

## Internal Segment Rolling

The server supports arbitrarily long audio streams from a single utterance by internally splitting the audio into bounded vLLM segments. This is transparent to the client — you send one continuous stream and receive one continuous transcript.

### How It Works

1. Audio chunks accumulate toward a **segment target** (`STT_SEGMENT_SECONDS`, default: 60s).
2. When the target is reached, the server finalizes the current vLLM segment (suppressing its `done` frame from the client) and immediately starts a new one.
3. A small **audio overlap** (`STT_SEGMENT_OVERLAP_SECONDS`, default: 0.8s) is replayed at the start of the new segment to improve transcription accuracy at boundaries.
4. The segment target is also capped so that audio tokens never exceed `VLLM_MAX_MODEL_LEN - 128` headroom tokens.

### Configuration

| Variable | Default | Notes |
|----------|---------|-------|
| `STT_INTERNAL_ROLL` | `true` | Enable/disable segment rolling. Disable only if you handle segmentation yourself. |
| `STT_SEGMENT_SECONDS` | `60` | Target segment length before rolling (seconds). |
| `STT_SEGMENT_OVERLAP_SECONDS` | `0.8` | Audio overlap replayed at segment boundaries (seconds). |
| `STT_MAX_BACKLOG_SECONDS` | `5` | Max unprocessed audio backlog before dropping oldest chunks. |

### Backlog Management

When inbound audio accumulates faster than vLLM can process it (e.g. under high concurrency or GPU contention), the server drops the **oldest** unprocessed chunks once the backlog exceeds `STT_MAX_BACKLOG_SECONDS`. When this happens, the server emits a `status` frame:

```json
{
  "type": "status",
  "payload": {
    "kind": "overload_drop",
    "dropped_seconds": 1.2,
    "max_backlog_seconds": 5.0,
    "source": "pending_buffer"
  }
}
```

This keeps the stream live and minimizes latency at the cost of a small transcription gap.

## Connection Management

### Long-Lived Connections

The server supports WebSocket connections lasting hours or days with many utterances per connection:

- Each utterance is scoped by `request_id`.
- After receiving `done`, start a new utterance with a fresh `request_id`.
- Send application-level `ping` messages periodically to prevent idle timeout (or set `WS_IDLE_TIMEOUT_S=0`).

### Keep-Alive Pattern

```json
{"type":"ping","session_id":"s1","request_id":"keepalive","payload":{}}
```

Send this at least once per idle timeout interval. The server responds with `pong` and resets the idle timer.

### Infinite Streaming

For continuous audio (e.g. a live microphone feed that runs indefinitely):

1. Open a single WebSocket connection.
2. Send `commit final=false` once.
3. Stream `append` messages continuously.
4. The server handles segment boundaries internally (see [Internal Segment Rolling](#internal-segment-rolling)).
5. When you want to stop, send `commit final=true` — or just close the socket.

## Capacity and Latency Notes

Two latency components matter for real-time transcription:

- **Model-inherent delay:** `VOXTRAL_TRANSCRIPTION_DELAY_MS` (80..2400ms). This is a floor — no amount of hardware can beat it.
- **System overhead:** batching/scheduling, GPU contention, network buffering. Scales with concurrency.

### Practical Tuning Levers

- **Keep sessions short and finalize quickly.** Each active utterance holds KV cache.
- **FP8 KV cache** halves KV memory on supported GPUs (Ada/Hopper+), roughly doubling concurrency. Enabled automatically when the GPU supports it.
- **Lower `VLLM_MAX_MODEL_LEN`** reduces per-sequence KV cost (the server rolls segments internally to compensate).
- **`max_num_batched_tokens`** controls the throughput/tail-latency tradeoff. Edit `src/runtime/gpu_profiles.py` to change it (intentionally not env-configurable).

## GPU Profiles

`max_num_batched_tokens` is selected per-GPU at startup to balance throughput and tail latency:

| GPU | `max_num_batched_tokens` |
|-----|--------------------------|
| H100 | `4096` |
| B200 | `4096` |
| RTX 9000 | `4096` |
| L40S | `2048` |
| L40 | `2048` |
| RTX 6000 | `2048` |
| A100 | `2048` |
| Other / undetected | `2048` |

The selection logic matches against the GPU name reported by `torch.cuda.get_device_name()` (falling back to `nvidia-smi`). See `src/runtime/gpu_profiles.py`.

### Auto-Tuning max_num_seqs

When `VLLM_MAX_NUM_SEQS` is not set, the server estimates the maximum safe number of concurrent sequences by computing how many fit in the KV cache budget:

```
budget = (GPU_total_memory * gpu_memory_utilization - weight_bytes) * 0.90
per_seq_bytes = 2 * n_layers * n_kv_heads * head_dim * kv_bytes_per_element * kv_tokens
max_num_seqs = budget / per_seq_bytes  (capped at 512)
```

Where `kv_tokens = min(max_model_len, sliding_window - 1 + max_num_batched_tokens)` for sliding-window models.

Set `VLLM_MAX_NUM_SEQS` explicitly to bypass this estimate.

## Test Clients

All clients live under `tests/e2e/` and speak the WebSocket envelope protocol. Common flags:

| Flag | Description |
|------|-------------|
| `--server` | `host:port`, `ws://host:port`, or full URL |
| `--secure` | Use WSS instead of WS |
| `--debug` | Print debug info and raw server messages |
| `--voxtral-key` | API key (overrides `VOXTRAL_API_KEY` env) |

### Warmup

Single utterance with timing metrics. Use as a quick health check after deployment.

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.warmup --server localhost:8000
VOXTRAL_API_KEY=secret python -m tests.e2e.warmup --server localhost:8000 --file short.wav --debug
```

| Flag | Default | Description |
|------|---------|-------------|
| `--file` | `mid.wav` | Audio file (name in `samples/` or absolute path) |
| `--full-text` | off | Print full transcript (default: truncate to 80 chars) |

### Benchmark

Concurrent load generator with p50/p95 summaries and throughput metrics.

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.bench --server localhost:8000 --n 100 --concurrency 100
```

| Flag | Default | Description |
|------|---------|-------------|
| `--n` | `20` | Total number of sessions |
| `--concurrency` | `5` | Max concurrent sessions |
| `--file` | `mid.wav` | Audio file |

### Idle Timeout

Opens a connection, sends nothing, and waits for the server to close it. Validates that idle timeout enforcement works correctly.

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.idle --server localhost:8000
```

| Flag | Default | Description |
|------|---------|-------------|
| `--grace-period` | config default | Extra seconds to wait beyond idle timeout |

### Conversation

Two audio files streamed over a single WebSocket connection with an artificial pause between them. Validates multi-utterance session handling.

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.convo --server localhost:8000
VOXTRAL_API_KEY=secret python -m tests.e2e.convo --server localhost:8000 --file1 short.wav --file2 mid.wav --pause-s 5
```

| Flag | Default | Description |
|------|---------|-------------|
| `--file1` | `mid.wav` | First audio file |
| `--file2` | `realistic.mp3` | Second audio file |
| `--pause-s` | `3.0` | Silence between segments (seconds) |
| `--full-text` | off | Print full combined transcript |

### Remote

Warmup-equivalent designed for remote GPU deployments. Same flags as warmup.

```bash
VOXTRAL_API_KEY=secret python -m tests.e2e.remote --server your-gpu-host:8000
```

## Environment Variables

Every environment variable the server reads. All are optional unless noted.

### Required

```bash
export VOXTRAL_API_KEY="your-secret-key"  # authenticates every WebSocket connection
```

### Recommended

```bash
export HF_TOKEN="hf_..."  # Hugging Face token for model downloads (avoids rate limits)
```

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_BIND_HOST` | `0.0.0.0` | Host the HTTP server binds to |
| `SERVER_PORT` | `8000` | Port the HTTP server listens on |
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Model

| Variable | Default | Description |
|----------|---------|-------------|
| `VOXTRAL_MODEL_ID` | `mistralai/Voxtral-Mini-4B-Realtime-2602` | Hugging Face model repo ID |
| `VOXTRAL_SERVED_MODEL_NAME` | same as `VOXTRAL_MODEL_ID` | Model name exposed in the realtime protocol |
| `VOXTRAL_TRANSCRIPTION_DELAY_MS` | `400` | Intentional transcription delay (multiple of 80, range 80..2400) |
| `VOXTRAL_MODEL_DIR` | `models/voxtral` | Writable local snapshot directory |

### Connection Lifecycle

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_CONNECTIONS` | `0` (auto) | Max concurrent WebSocket connections. `0` = auto from tuned `max_num_seqs` |
| `WS_IDLE_TIMEOUT_S` | `150` | Idle close timeout (seconds). `0` to disable |
| `WS_WATCHDOG_TICK_S` | `5` | Watchdog poll interval (seconds) |
| `WS_MAX_CONNECTION_DURATION_S` | `5400` | Hard max connection duration (seconds). `0` to disable |
| `WS_INBOUND_QUEUE_MAX` | `256` | Per-connection inbound message queue size |
| `WS_CLOSE_UNAUTHORIZED_CODE` | `1008` | WebSocket close code for auth failure |
| `WS_CLOSE_BUSY_CODE` | `1013` | WebSocket close code for server at capacity |
| `WS_CLOSE_IDLE_REASON` | `idle_timeout` | Close reason string for idle timeout |

### vLLM Engine

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_DTYPE` | `bfloat16` | Model dtype |
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.92` | Fraction of GPU memory for KV cache |
| `VLLM_MAX_MODEL_LEN` | `1024` | Per-segment context limit (audio+text tokens) |
| `VLLM_MAX_NUM_SEQS` | `128` | Max concurrent sequences. Unset to enable auto-tuning |
| `VLLM_ENFORCE_EAGER` | `false` | Disable CUDA graphs |
| `VLLM_KV_CACHE_DTYPE` | `auto` | KV cache dtype. Auto-selects `fp8` on capable GPUs |
| `VLLM_CALCULATE_KV_SCALES` | `false` | Dynamic KV scale calculation (auto-enabled with FP8 KV) |
| `VLLM_COMPILATION_CONFIG` | `{"cudagraph_mode":"PIECEWISE"}` | JSON dict for compilation config. `null` to disable |
| `VLLM_DISABLE_COMPILE_CACHE` | `true` | Disable the vLLM compile cache |

### Streaming

| Variable | Default | Description |
|----------|---------|-------------|
| `STT_INTERNAL_ROLL` | `true` | Enable internal segment rolling for long streams |
| `STT_SEGMENT_SECONDS` | `60` | Target segment length before rolling (seconds) |
| `STT_SEGMENT_OVERLAP_SECONDS` | `0.8` | Audio overlap at segment boundaries (seconds) |
| `STT_MAX_BACKLOG_SECONDS` | `5` | Max unprocessed audio backlog before dropping oldest |

### Launcher / Install

| Variable | Default | Description |
|----------|---------|-------------|
| `TORCH_BACKEND` | auto-detected | PyTorch wheel tag (`cu126`, `cu127`, `cu128`) |
| `PYTORCH_CUDA_INDEX_URL` | auto-detected | PyTorch CUDA wheel index URL |
| `TAIL_LOGS` | `1` | Set to `0` to skip log tailing after server start |

### Fixed Values (Not Env-Configurable)

These are hardcoded in `src/config/vllm.py` and `src/runtime/gpu_profiles.py`:

| Setting | Value | Reason |
|---------|-------|--------|
| `tokenizer_mode` | `mistral` | Required for Voxtral weight format |
| `config_format` | `mistral` | Required for Voxtral weight format |
| `load_format` | `mistral` | Required for Voxtral weight format |
| `max_num_batched_tokens` | Per-GPU | Throughput/latency tradeoff — see [GPU Profiles](#gpu-profiles) |

## Troubleshooting

### vLLM Install Fails

**Symptom:** pip/uv errors during `scripts/main.sh`, PyTorch/CUDA version mismatches.

**Cause:** Auto-detected CUDA version doesn't match the installed driver, or `uv` is not available.

**Fix:**
1. Confirm you are on a GPU host with a working NVIDIA driver.
2. Check the auto-detected `TORCH_BACKEND` in the install output.
3. Override manually if needed: `export TORCH_BACKEND=cu126 PYTORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu126`.
4. Run `bash scripts/lib/doctor.sh` to verify `torch.version.cuda` is `12.x`.

### Model Download Is Slow or Fails

**Symptom:** Server startup hangs at model download or fails with HTTP 429/403.

**Cause:** Missing Hugging Face token or network issues.

**Fix:**
1. Set `HF_TOKEN` to a valid Hugging Face token.
2. Ensure the snapshot directory (`models/voxtral` by default) is writable.
3. For air-gapped environments, manually populate `VOXTRAL_MODEL_DIR` with the model files.

### No token Events

**Symptom:** Client receives `final` and `done` but no `token` frames.

**Cause:** The audio is silence, or `transcription_delay_ms` delays partials beyond the audio duration.

**Fix:**
1. Verify you are sending actual speech audio, not silence.
2. Try a lower `VOXTRAL_TRANSCRIPTION_DELAY_MS` (e.g. `160`).
3. Use a longer audio sample to confirm partials appear.

### Inbound Queue Full

**Symptom:** Server closes the connection with `reason_code: "inbound_queue_full"`.

**Cause:** The client is sending messages faster than the server can dequeue them.

**Fix:**
1. Use 80ms audio chunks (matches Voxtral's step) instead of very small chunks.
2. Reduce per-connection message rate.
3. Increase `WS_INBOUND_QUEUE_MAX` conservatively — values that are too high increase memory use and tail latency.

### OOM / Capacity Issues

**Symptom:** Server crashes with CUDA OOM, or throughput degrades severely under load.

**Cause:** Too many concurrent sequences for available GPU memory.

**Fix:**
1. Lower `VLLM_GPU_MEMORY_UTILIZATION` slightly (e.g. `0.88`) if seeing intermittent OOM.
2. Lower `VLLM_MAX_NUM_SEQS` to reduce peak concurrency.
3. Lower `VLLM_MAX_MODEL_LEN` (e.g. `512`) to reduce per-sequence KV cost. The server compensates with more frequent segment rolls.
4. Enable FP8 KV cache if not already active (`VLLM_KV_CACHE_DTYPE=fp8`).

### Connection Rejected (at Capacity)

**Symptom:** WebSocket connection closes immediately with code `1013` and error `server_at_capacity`.

**Cause:** The server has reached `MAX_CONCURRENT_CONNECTIONS`.

**Fix:**
1. Wait for existing connections to finish.
2. If the limit seems too low, check the auto-tuned `max_num_seqs` in the server logs.
3. Set `MAX_CONCURRENT_CONNECTIONS` explicitly if the auto value is too conservative.

### Idle Timeout Too Aggressive

**Symptom:** Long pauses between utterances cause the connection to close with code `4000`.

**Cause:** `WS_IDLE_TIMEOUT_S` is shorter than your inter-utterance gap.

**Fix:**
1. Send periodic `ping` messages during pauses to reset the idle timer.
2. Increase `WS_IDLE_TIMEOUT_S` (e.g. `300` for 5 minutes).
3. Set `WS_IDLE_TIMEOUT_S=0` to disable idle timeout entirely (not recommended for shared deployments).
