# Docker (vLLM)

This repo does not ship a prebuilt image. The Docker assets here are scaffolding
only, intended to mirror the deployment style used in other Yap repos.

Key notes:
- Voxtral Realtime relies on vLLM Realtime support.
- The official model guidance recommends installing vLLM from the nightly wheel
  index (`https://wheels.vllm.ai/nightly`) and using the audio deps stack.
- You must provide `VOXTRAL_API_KEY` at runtime.

Example run (after building your image):
```bash
docker run --rm -it --gpus all -p 8000:8000 \
  -e VOXTRAL_API_KEY=secret_token \
  -e HF_TOKEN=hf_... \
  -e MAX_CONCURRENT_CONNECTIONS=100 \
  yourimage:tag
```

