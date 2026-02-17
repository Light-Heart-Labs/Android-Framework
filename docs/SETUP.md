# Running OpenClaw Locally — Full Setup Guide

This guide walks you through running an OpenClaw agent entirely on your own
hardware using vLLM. Zero cloud APIs, zero per-token costs, zero data leaving
your network.

**Time to complete:** ~15 minutes (plus model download time)

## Prerequisites

| What | Why |
|------|-----|
| Linux server with NVIDIA GPU | vLLM requires CUDA. 96GB VRAM for Qwen3-Coder-Next-FP8, 24GB+ for smaller models |
| Docker + NVIDIA Container Toolkit | Easiest way to run vLLM |
| Python 3.10+ with pip | For the tool call proxy |
| Node.js 22+ | For OpenClaw |

> **Same machine or separate machines?** Everything can run on one machine.
> If you have a dedicated GPU server, run vLLM + proxy there and OpenClaw
> wherever you want — just update the URLs.

## Architecture

```
You ←→ OpenClaw Gateway ←→ Tool Call Proxy (:8003) ←→ vLLM (:8000)
         (agent loop)      (SSE re-wrap +            (model inference)
                            tool extraction)
```

**Why the proxy?** OpenClaw always requests streaming responses, but tool call
extraction requires seeing the full response. The proxy intercepts requests with
tools, forces non-streaming, extracts tool calls from the model's text output,
then re-wraps everything as SSE chunks that OpenClaw expects. Without it, you
get "No reply from agent" with 0 tokens. See [ARCHITECTURE.md](ARCHITECTURE.md)
for the deep dive.

---

## Step 1: Start vLLM

```bash
# Default: Qwen3-Coder-Next-FP8 (80B MoE, needs ~75GB VRAM)
./scripts/start-vllm.sh

# Or customize the model:
VLLM_MODEL="Qwen/Qwen3-8B" VLLM_TOOL_PARSER="hermes" ./scripts/start-vllm.sh
```

Wait for "vLLM is ready!" — model loading takes 60-120 seconds.

**Verify:**
```bash
curl http://localhost:8000/v1/models
```

### Choosing a Model

| Model | VRAM | Context | Tool Parser | Notes |
|-------|------|---------|-------------|-------|
| Qwen/Qwen3-Coder-Next-FP8 | ~75GB | 128K | `qwen3_coder` | Best for coding agents. 80B MoE, 3B active. |
| Qwen/Qwen3-8B | ~16GB | 32K | `hermes` | Good starter model for consumer GPUs |
| Qwen/Qwen3-32B | ~32GB | 32K | `hermes` | Strong mid-range option |

> **Critical:** Match the `--tool-call-parser` to your model. Wrong parser =
> broken tool calls. Qwen3-Coder-Next uses `qwen3_coder`, most others use `hermes`.

### vLLM Flags That Matter

| Flag | What | Why |
|------|------|-----|
| `--gpu-memory-utilization 0.92` | VRAM allocation | 0.95 can cause OOM crashes. 0.92 is safe. |
| `--compilation_config.cudagraph_mode=PIECEWISE` | CUDA graph compilation mode | Prevents illegal memory access with DeltaNet architectures |
| `--enable-auto-tool-choice` | Allow model to decide when to use tools | Required for tool calling |
| `--kv-cache-dtype` | KV cache precision | Do NOT use `fp8` with Qwen3-Next — causes assertion errors |

---

## Step 2: Start the Tool Call Proxy

```bash
# Install dependencies
pip3 install flask requests

# Start the proxy
./scripts/start-proxy.sh

# Or customize:
PROXY_PORT=8003 VLLM_URL=http://localhost:8000 ./scripts/start-proxy.sh
```

**Verify:**
```bash
curl http://localhost:8003/health
# Expected: {"status":"ok","vllm_url":"http://localhost:8000","max_tool_calls":500}
```

---

## Step 3: Install OpenClaw

```bash
sudo npm install -g openclaw@latest
openclaw --version
```

Run initial setup if this is a fresh install:
```bash
openclaw setup
```

---

## Step 4: Configure OpenClaw

Copy the config template:
```bash
cp configs/openclaw.json ~/.openclaw/openclaw.json
```

**If vLLM is on a different machine**, edit the `baseUrl`:
```bash
# Edit ~/.openclaw/openclaw.json
# Change "http://localhost:8003/v1" to "http://YOUR_GPU_SERVER:8003/v1"
```

Delete any auto-generated models cache (forces OpenClaw to re-read your config):
```bash
rm -f ~/.openclaw/agents/main/agent/models.json
```

Set the API key (can be anything — vLLM doesn't validate it, but OpenClaw requires one):
```bash
export VLLM_API_KEY=vllm-local
# Or add to your shell profile:
echo 'export VLLM_API_KEY=vllm-local' >> ~/.bashrc
```

### Critical Config: The `compat` Block

The `compat` section in `openclaw.json` is the most important part. Without it,
OpenClaw sends parameters that vLLM rejects silently:

```json
"compat": {
  "supportsStore": false,
  "supportsDeveloperRole": false,
  "supportsReasoningEffort": false,
  "maxTokensField": "max_tokens"
}
```

| Field | Why |
|-------|-----|
| `supportsStore: false` | OpenClaw sends `store: false` by default. vLLM rejects unknown params. |
| `supportsDeveloperRole: false` | Prevents sending `developer` role messages vLLM doesn't understand. |
| `supportsReasoningEffort: false` | Prevents sending reasoning effort params. |
| `maxTokensField: "max_tokens"` | OpenClaw defaults to `max_completion_tokens`. vLLM wants `max_tokens`. |

---

## Step 5: Test It

Quick text test:
```bash
VLLM_API_KEY=vllm-local openclaw agent --local --agent main -m 'What is 2+2?'
```

Tool calling test:
```bash
VLLM_API_KEY=vllm-local openclaw agent --local --agent main -m 'List the files in /tmp'
```

If both return sensible output, you're running a fully local AI agent.

---

## Step 6 (Optional): Run as a Service

For always-on operation, set up a systemd user service:

```bash
# Copy the service file
mkdir -p ~/.config/systemd/user
cp configs/openclaw-gateway.service ~/.config/systemd/user/

# Enable and start
systemctl --user daemon-reload
systemctl --user enable openclaw-gateway.service
systemctl --user start openclaw-gateway.service

# Check status
systemctl --user status openclaw-gateway.service
```

---

## Step 7 (Optional): Add Workspace Personality

OpenClaw injects workspace files into every agent session. Copy the starter
templates to customize your agent's personality:

```bash
cp -r workspace/ ~/.openclaw/workspace/
```

Edit the files to make the agent yours:
- `SOUL.md` — Core personality and principles
- `IDENTITY.md` — Name, role, vibe
- `TOOLS.md` — What tools and services are available
- `MEMORY.md` — Working memory that persists across sessions

---

## Step 8 (Optional): Enable Session Cleanup

Long-running agents accumulate conversation history until they exceed the
model's context window and crash. The session watchdog prevents this:

```bash
# Edit config.yaml with your preferences
nano config.yaml

# Install the session cleanup timer
./install.sh --cleanup-only
```

---

## Troubleshooting

### "No reply from agent" with 0 tokens

**Cause:** SSE re-wrapping not working. OpenClaw expects SSE but got nothing.

**Fix:** Make sure `baseUrl` in openclaw.json points to port **8003** (proxy),
not 8000 (vLLM). Test the proxy directly:

```bash
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-Coder-Next-FP8","messages":[{"role":"user","content":"hi"}],"stream":true}'
```

You should see `data: {...}\n\n` SSE chunks ending with `data: [DONE]`.

### Config validation errors on startup

**Cause:** Using unsupported compat fields.

**Fix:** Only use these four validated fields:
- `supportsStore`
- `supportsDeveloperRole`
- `supportsReasoningEffort`
- `maxTokensField`

### Tool calls returned as plain text

**Cause:** Proxy not extracting, or OpenClaw bypassing proxy.

**Fix:** Verify `baseUrl` points to port 8003. Check proxy logs:
```bash
tail -f /tmp/vllm-proxy.log
```

### Agent stuck in a repetition loop

**Cause:** Model limitation with complex multi-step tool chains.

**Mitigation:** The proxy aborts after 500 tool calls (configurable via
`MAX_TOOL_CALLS` env var). For complex tasks, keep prompts single-action.

### vLLM crashes with CUDA illegal memory access

**Cause:** Default cudagraph mode incompatible with hybrid architectures.

**Fix:** Add `--compilation_config.cudagraph_mode=PIECEWISE` to docker run.

### vLLM crashes with assertion error on startup

**Cause:** Using `--kv-cache-dtype fp8` with Qwen3-Next.

**Fix:** Remove that flag. FP8 model weights are fine; FP8 KV cache is not
supported for this architecture.

### vLLM rejects `store` parameter

**Fix:** Add `"supportsStore": false` to the compat section.

### vLLM rejects `max_completion_tokens`

**Fix:** Add `"maxTokensField": "max_tokens"` to the compat section.

---

## Using a Different Model

To swap models, update three things:

1. **vLLM** — Change the `--model` and `--tool-call-parser` flags
2. **Proxy** — No changes needed (it's model-agnostic)
3. **OpenClaw config** — Update `id`, `name`, `contextWindow`, `maxTokens` in
   `openclaw.json` and delete `~/.openclaw/agents/main/agent/models.json`

Example for Qwen3-8B:
```bash
# 1. Start vLLM with different model
VLLM_MODEL="Qwen/Qwen3-8B" \
VLLM_TOOL_PARSER="hermes" \
VLLM_MAX_LEN=32768 \
./scripts/start-vllm.sh

# 2. Update openclaw.json model ID, contextWindow, maxTokens

# 3. Clear models cache
rm -f ~/.openclaw/agents/main/agent/models.json
```

---

## Adding Discord

To connect your agent to Discord, add a `channels` section to `openclaw.json`:

```json
"channels": {
  "discord": {
    "token": "YOUR_BOT_TOKEN",
    "guilds": {
      "YOUR_GUILD_ID": {
        "channels": {
          "YOUR_CHANNEL_ID": {
            "allow": true,
            "requireMention": false
          }
        }
      }
    }
  }
},
"plugins": {
  "entries": {
    "discord": {
      "enabled": true
    }
  }
}
```

Set `requireMention: false` for channels where the agent should respond to
every message, or `true` for channels where it only responds when @mentioned.

---

## Further Reading

- [Cookbook recipes](cookbook/README.md) — Step-by-step guides for voice agents,
  document Q&A, code assistants, multi-GPU clusters, and more
- [research/HARDWARE-GUIDE.md](research/HARDWARE-GUIDE.md) — GPU buying guide
  with tier rankings, used market analysis, and price-performance comparisons
