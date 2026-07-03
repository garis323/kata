# SN60 model-pinning relay

Forces every miner-agent inference request onto a single pinned model, so a miner
cannot spend the validator's inference budget on a costlier model or win a duel by
using a bigger one.

## Why this exists

Miner agents run in a Docker container on the **internal** `bitsec-net` network,
which has no internet access. Their only route to a provider is the inference
endpoint Kata hands them via `KATA_SN60_INFERENCE_API`. Point that at this relay
and it overwrites the `model` field of every `POST /inference` request before
forwarding to the real Bitsec proxy.

Because enforcement happens on the actual API call — not by scanning submitted
source — a runtime-computed or obfuscated model string cannot bypass it: the agent
has no other way out. The scorer is unaffected; it uses a separate endpoint
(`localhost:8087`, Chutes) that never passes through this relay.

```
miner agent (no egress) ──▶ kata_model_relay ──▶ bitsec_proxy ──▶ OpenRouter
                                  │
                                  └─ request "model" → qwen/qwen3.6-35b-a3b
```

## Deploy

1. **Build** (from the kata repo root):

   ```bash
   docker build -f deploy/sn60-model-relay/Dockerfile -t kata-sn60-model-relay .
   ```

2. **Run** it on the same internal network the agents use:

   ```bash
   docker run -d --restart unless-stopped \
     --name kata_model_relay --network bitsec-net \
     -e KATA_RELAY_UPSTREAM=http://bitsec_proxy:8000 \
     -e KATA_RELAY_PINNED_MODEL=qwen/qwen3.6-35b-a3b \
     kata-sn60-model-relay
   ```

3. **Point the validator at it.** In the validator's environment set:

   ```
   KATA_SN60_INFERENCE_API=http://kata_model_relay:8000
   ```

   (The default without this is `http://bitsec_proxy:8000`, i.e. no pinning.)

## Verify

The relay answers its own health check without touching the upstream proxy:

```bash
docker exec kata_model_relay python -c \
  "import urllib.request,json; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/healthz')))"
# {'status': 'ok', 'pinned_model': 'qwen/qwen3.6-35b-a3b'}
```

## Configuration

| Env var                   | Default                        | Meaning                                  |
| ------------------------- | ------------------------------ | ---------------------------------------- |
| `KATA_RELAY_UPSTREAM`     | `http://bitsec_proxy:8000`     | Real inference proxy to forward to       |
| `KATA_RELAY_PINNED_MODEL` | `qwen/qwen3.6-35b-a3b`         | Model every inference request is forced onto |
| `KATA_RELAY_HOST`         | `0.0.0.0`                      | Bind host                                |
| `KATA_RELAY_PORT`         | `8000`                         | Bind port                                |
| `KATA_RELAY_TIMEOUT`      | `900`                          | Upstream request timeout (seconds)       |
