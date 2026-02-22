# Dream Server Mode Switch

*Part of M1 Zero-Cloud Initiative — Phase 3*

One-command switching between cloud, local, and hybrid modes.

---

## Quick Start

```bash
# Check current mode
dream mode status

# Switch to local mode (100% offline)
dream mode local

# Switch to cloud mode (full API access)
dream mode cloud

# Switch to hybrid mode (local-first + cloud fallback)
dream mode hybrid
```

---

## Modes

### Cloud Mode
Full access to cloud AI providers through LiteLLM gateway.

| Aspect | Details |
|--------|---------|
| **LLM** | Claude, GPT-4, Llama via Together AI |
| **Quality** | Best-in-class |
| **Cost** | ~$0.003-0.06/1K tokens |
| **Requires** | Internet, API keys |
| **Web Search** | ✅ Enabled |

**Best for:** Maximum quality, complex tasks, when cost isn't a concern.

```bash
dream mode cloud
```

**Required .env variables:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
# Or Together AI for open source models:
TOGETHER_API_KEY=...
```

---

### Local Mode
100% offline operation. All inference runs on your hardware.

| Aspect | Details |
|--------|---------|
| **LLM** | Qwen 32B via vLLM |
| **Quality** | Very good |
| **Speed** | 10-15 tok/s (GPU) |
| **Cost** | $0 (electricity only) |
| **Requires** | GPU (24GB+ VRAM), pre-downloaded models |
| **Web Search** | ❌ Disabled |

**Best for:** Privacy-critical workloads, offline environments, cost savings.

```bash
dream mode local
```

**Pre-requisites:**
```bash
# Download models before switching
huggingface-cli download Qwen/Qwen2.5-32B-Instruct-AWQ --local-dir ./models/

# Download Whisper model
# (happens automatically on first use, but better to do while online)
```

---

### Hybrid Mode
Local-first with automatic cloud fallback. Best of both worlds.

| Aspect | Details |
|--------|---------|
| **LLM** | Local Qwen → Cloud fallback |
| **Quality** | Local quality + cloud reliability |
| **Cost** | $0 normally, cloud rates on fallback |
| **Requires** | GPU + API keys (optional) |
| **Web Search** | ✅ Enabled |

**Best for:** Daily use — get privacy/speed benefits of local with cloud as safety net.

```bash
dream mode hybrid
```

**Fallback triggers:**
- Local model timeout (default: 30s)
- Local model error (5xx, connection refused)
- Empty/invalid response from local

**Configure fallback in .env:**
```bash
HYBRID_FALLBACK_TIMEOUT=30      # Seconds before fallback
HYBRID_FALLBACK_ENABLED=true    # Enable/disable fallback
```

---

## Architecture

### Cloud Mode
```
User → Open WebUI → LiteLLM → Cloud APIs (Claude/GPT-4/etc.)
```

### Local Mode
```
User → Open WebUI → vLLM (local) → Response
                    ↑
                    No network required
```

### Hybrid Mode
```
User → Open WebUI → LiteLLM → vLLM (local) → Response
                         ↓
                    [On timeout/error]
                         ↓
                    Cloud APIs (fallback)
```

---

## Files

| File | Purpose |
|------|---------|
| `docker-compose.cloud.yml` | Cloud mode configuration |
| `docker-compose.local.yml` | Local mode configuration |
| `docker-compose.hybrid.yml` | Hybrid mode configuration |
| `config/litellm/cloud-config.yaml` | LiteLLM cloud routing |
| `config/litellm/hybrid-config.yaml` | LiteLLM hybrid routing |
| `config/litellm/offline-config.yaml` | LiteLLM local-only routing |
| `.current-mode` | Stores current mode |

---

## Data Safety

**All modes share the same data volumes:**
- `./data/open-webui/` — Conversations, users
- `./data/qdrant/` — Vector database
- `./data/whisper/` — STT cache
- `./models/` — Downloaded models

**Switching modes preserves all data.** Only the services and routing change.

---

## Mode Comparison

| Feature | Cloud | Local | Hybrid |
|---------|-------|-------|--------|
| Internet required | ✅ | ❌ | ✅ (for fallback) |
| API keys required | ✅ | ❌ | Optional |
| GPU required | ❌ | ✅ | ✅ |
| Response quality | Best | Very good | Best of both |
| Response speed | 50-100 tok/s | 10-15 tok/s | Local speed or cloud |
| Cost | $$$  | $0 | $0 or $$$ |
| Privacy | Data to cloud | 100% local | Local unless fallback |
| Web search | ✅ | ❌ | ✅ |
| Reliability | High | GPU-dependent | Highest |

---

## Troubleshooting

### Local mode won't start
```bash
# Check GPU status
nvidia-smi

# Check models are downloaded
ls -la ./models/

# Check vLLM logs
dream logs vllm
```

### Hybrid fallback not working
```bash
# Check API keys are set
grep -E "ANTHROPIC|OPENAI|TOGETHER" .env

# Check LiteLLM logs
dream logs litellm
```

### Mode switch fails
```bash
# Manual stop all containers
docker compose down

# Check mode file
cat .current-mode

# Manual start with specific compose file
docker compose -f docker-compose.local.yml up -d
```

---

## CLI Reference

```bash
# Mode commands
dream mode              # Show current mode (same as status)
dream mode status       # Show current mode
dream mode cloud        # Switch to cloud mode
dream mode local        # Switch to local mode
dream mode hybrid       # Switch to hybrid mode

# Shorthand
dream m cloud           # Shorthand for mode cloud
```

---

## Related Documentation

- `docs/M1-ZERO-CLOUD-CONFIG-GUIDE.md` — Detailed zero-cloud configuration
- `QUICKSTART.md` — Getting started with Dream Server
- `FAQ.md` — Frequently asked questions

---

*M1 Zero-Cloud Initiative — Democratizing AI access*
