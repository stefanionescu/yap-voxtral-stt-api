# Advanced Guide

## Voxtral Realtime Latency: `transcription_delay_ms`

Voxtral Realtime is trained with an intentional transcription delay. This repo
sets the delay by patching the model’s `tekken.json` inside a writable snapshot
directory (default: `models/voxtral`).

Configure via:

```bash
export VOXTRAL_TRANSCRIPTION_DELAY_MS=400  # must be multiple of 80 (80..2400)
```

Notes:
- This is **not** currently a per-request knob in vLLM’s Realtime protocol.
- The server applies the patch before vLLM engine initialization.

## Environment Variables

### Required
- `VOXTRAL_API_KEY`: required for every WebSocket connection
- `MAX_CONCURRENT_CONNECTIONS`: connection capacity guard

### Recommended
- `HF_TOKEN`: used for model snapshot download (rate limits/private repos)

### Model
- `VOXTRAL_MODEL_ID` (default: `mistralai/Voxtral-Mini-4B-Realtime-2602`)
- `VOXTRAL_MODEL_DIR` (default: `models/voxtral`)
- `VOXTRAL_SERVED_MODEL_NAME` (default: same as `VOXTRAL_MODEL_ID`)
- `VOXTRAL_TRANSCRIPTION_DELAY_MS` (default: `400`)

### WebSocket
- `WS_IDLE_TIMEOUT_S` (default: `150`)
- `WS_MAX_CONNECTION_DURATION_S` (default: `5400` = 90 minutes)
- `WS_MESSAGE_WINDOW_SECONDS` / `WS_MAX_MESSAGES_PER_WINDOW` (default: `60` / `200`)
- `WS_CANCEL_WINDOW_SECONDS` / `WS_MAX_CANCELS_PER_WINDOW` (default: `60` / `50`)

### vLLM
- `VLLM_GPU_MEMORY_UTILIZATION` (default: `0.92`)
- `VLLM_MAX_NUM_SEQS` (default: `128`)
- `VLLM_MAX_NUM_BATCHED_TOKENS` (default: `4096`)
- `VLLM_MAX_MODEL_LEN` (default: `67500` ~= 90 minutes @ 80ms/token)
- `VLLM_KV_CACHE_DTYPE` (default: `auto`, optional: FP8 variants on L40S/H100)
- `VLLM_ENFORCE_EAGER` (default: `false`)
- `VLLM_TOKENIZER_MODE` / `VLLM_CONFIG_FORMAT` / `VLLM_LOAD_FORMAT` (default: `mistral`)

Voxtral streaming timing notes:
- Voxtral Realtime uses an ~80ms step (12.5Hz), so you can approximate:
  - `max_seconds ~= VLLM_MAX_MODEL_LEN * 0.08`
  - `VLLM_MAX_MODEL_LEN ~= max_seconds / 0.08`

## WebSocket Protocol (`/ws`)

This server uses a Yap-style envelope and forwards vLLM Realtime events inside it.

Envelope:
```json
{"type":"...","session_id":"...","request_id":"...","payload":{...}}
```

Client -> Server:
- `ping`, `end`, `cancel`
- `session.update` (model selection; this server only allows the configured model)
- `input_audio_buffer.commit` (start/finalize utterance)
- `input_audio_buffer.append` (base64 PCM16 16kHz mono)

Server -> Client:
- `pong`, `session_end`, `cancelled`
- vLLM Realtime events: `session.created`, `session.updated`, `transcription.delta`, `transcription.done`, `error`

## Concurrency Notes (L40S)

For Voxtral Realtime, concurrency is often limited by **KV-cache memory** for long-lived
streams. If your workload is utterance-scoped (voice-agent style) and you close or
finalize frequently, 100 concurrent sessions on a single L40S is substantially more
realistic than 100 always-on meeting-length streams.

Practical levers:
- Keep sessions short and finalize quickly (`commit final=true`)
- Consider KV cache compression (FP8 KV cache) if supported by your vLLM build
- Tune batching (`VLLM_MAX_NUM_BATCHED_TOKENS`) to balance throughput vs tail latency
