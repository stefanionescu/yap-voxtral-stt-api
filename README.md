# Yap Voxtral STT API

Streaming speech-to-text (STT) server for **Mistral Voxtral Realtime** using **vLLM**.

- FastAPI + WebSocket endpoint: `GET /ws`
- Yap-style message envelope: `{type, session_id, request_id, payload}`
- vLLM Realtime protocol semantics inside the envelope (`session.update`, `input_audio_buffer.*`, `transcription.*`)
- Capacity guard, ping/pong keepalive, and idle timeout

## Contents

- [Quickstart](#quickstart)
- [WebSocket API](#websocket-api)
- [Stopping and Restarting](#stopping-and-restarting)
- [Testing](#testing)
- [Linting](#linting)
- [Docker](#docker)
- [Advanced Guide](ADVANCED.md)

## Quickstart

Set required environment variables:

```bash
export VOXTRAL_API_KEY="secret_token"
export HF_TOKEN="hf_your_token"
export MAX_CONCURRENT_CONNECTIONS=100
export WS_MAX_CONNECTION_DURATION_S=5400  # 90 minutes (optional)
```

Start the server:

```bash
bash scripts/main.sh
```

Health check:

```bash
curl -s http://localhost:8000/healthz
```

## WebSocket API

Connect:

```text
ws://server:8000/ws?api_key=VOXTRAL_API_KEY
```

All messages use this envelope:

```json
{
  "type": "...",
  "session_id": "stable-user-id",
  "request_id": "utterance-id",
  "payload": { }
}
```

### Ping / End / Cancel

```json
{"type":"ping","session_id":"s1","request_id":"r1","payload":{}}
{"type":"end","session_id":"s1","request_id":"r2","payload":{}}
{"type":"cancel","session_id":"s1","request_id":"r3","payload":{"reason":"client_request"}}
```

### Realtime STT (vLLM semantics)

1. (Optional) update the session model (this server only supports one model):

```json
{"type":"session.update","session_id":"s1","request_id":"r1","payload":{"model":"mistralai/Voxtral-Mini-4B-Realtime-2602"}}
```

2. Start an utterance:

```json
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":false}}
```

3. Stream audio chunks (PCM16 16kHz mono, base64):

```json
{"type":"input_audio_buffer.append","session_id":"s1","request_id":"utt-1","payload":{"audio":"<base64 pcm16>"}} 
```

4. Finalize:

```json
{"type":"input_audio_buffer.commit","session_id":"s1","request_id":"utt-1","payload":{"final":true}}
```

Server events (wrapped vLLM Realtime events):
- `session.created`, `session.updated`
- `transcription.delta` (payload contains `delta`)
- `transcription.done` (payload contains `text`)
- `error`

See `ADVANCED.md` for protocol details and test client examples.

## Stopping and Restarting

```bash
bash scripts/stop.sh
bash scripts/restart.sh
```

Full cleanup:
```bash
FULL_CLEANUP=1 bash scripts/stop.sh
```

## Testing

Install client deps:

```bash
bash scripts/activate.sh
pip install -r requirements-dev.txt
```

Warmup:
```bash
VOXTRAL_API_KEY=secret_token python tests/e2e/warmup.py
```

Benchmark:
```bash
VOXTRAL_API_KEY=secret_token python tests/e2e/bench.py --requests 32 --concurrency 32
```

Idle timeout:
```bash
VOXTRAL_API_KEY=secret_token python tests/e2e/idle.py
```

Max connection duration (server must be started with a small `WS_MAX_CONNECTION_DURATION_S` to test quickly):
```bash
VOXTRAL_API_KEY=secret_token python tests/e2e/max_duration.py --expect-seconds 2 --grace-seconds 5
```

## Linting

```bash
pip install -r requirements-dev.txt
bash scripts/lint.sh
bash scripts/lint.sh --fix
```

Enable git hooks:
```bash
git config core.hooksPath .githooks
```

## Docker

See `docker/README.md`.
