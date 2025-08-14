# Everday Local Agent 

This projects aims to create a Jarvis like local assistant, capable of getting text and audio prompts, making researches, excute code and bash commands and give spoken responses.

## 1) Agent

I used gpt5 from openrouter for this project, and smolagents as the agentic framework.

## 2) Speech 

### Local speaking model with OpenAudio

I installed OpenAudio via Pinokio and ran the local API server script inside /app/tools

```bash
python -m tools.api_server \
  --listen 0.0.0.0:8080 \
  --llama-checkpoint-path "checkpoints/openaudio-s1-mini" \
  --decoder-checkpoint-path "checkpoints/openaudio-s1-mini/codec.pth" \
  --decoder-config-name modded_dac_vq \
  --device cuda --half
```

Expected start log:

```sql
2025-08-14 20:11:50.377 | INFO  | __main__:initialize_app:93 - Startup done, listening server at http://0.0.0.0:8080
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

#### Observed issues

The voice changes every response, decoder appears to sample a new speaker embedding by default.

Frequent OOM (on 6GB VRAM)

### with Google TTS

Using Google TTS is faster, consistent, and higher quality. The free tier provides 4 million free characters spoken.