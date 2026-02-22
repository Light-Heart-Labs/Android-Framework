# Dream Server

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](../LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Required-2496ED?logo=docker)](https://docs.docker.com/get-docker/)
[![NVIDIA](https://img.shields.io/badge/NVIDIA-GPU%20Accelerated-76B900?logo=nvidia)](https://developer.nvidia.com/cuda-toolkit)
[![n8n](https://img.shields.io/badge/n8n-Workflows-FF6D5A?logo=n8n)](https://n8n.io)

**Your turnkey local AI stack.** Buy hardware. Run installer. AI running.

---

## 5-Minute Quickstart

```bash
# One-line install (Linux/WSL)
curl -fsSL https://raw.githubusercontent.com/Light-Heart-Labs/Lighthouse-AI/main/dream-server/get-dream-server.sh | bash
```

Or manually:

```bash
git clone https://github.com/Light-Heart-Labs/Lighthouse-AI.git
cd Lighthouse-AI/dream-server
./install.sh
```

The installer auto-detects your GPU, picks the right model, generates secure passwords, and starts everything. Open **http://localhost:3000** and start chatting.

### 🚀 Instant Start (Bootstrap Mode)

By default, Dream Server uses **bootstrap mode** for instant gratification:

1. Starts immediately with a tiny 1.5B model (downloads in <1 minute)
2. You can start chatting within **2 minutes** of running the installer
3. The full model downloads in the background
4. When ready, run `./scripts/upgrade-model.sh` to hot-swap to the full model

No more staring at download bars. Start playing immediately.

To skip bootstrap and wait for the full model: `./install.sh --no-bootstrap`

### Windows

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Light-Heart-Labs/Lighthouse-AI/main/dream-server/install.ps1" -OutFile install.ps1
.\install.ps1
```

The Windows installer handles WSL2 setup, Docker Desktop, and NVIDIA drivers automatically.

**Requirements:** Windows 10 21H2+ or Windows 11, NVIDIA GPU, Docker Desktop

---

## What's Included

| Component | Purpose | Port |
|-----------|---------|------|
| **vLLM** | High-performance LLM inference | 8000 |
| **Open WebUI** | Beautiful chat interface | 3000 |
| **Dashboard** | System status, GPU metrics, service health | 3001 |
| **Privacy Shield** | PII redaction for external API calls | 8085 |
| **Whisper** | Speech-to-text (optional) | 9000 |
| **Kokoro** | Text-to-speech (optional) | 8880 |
| **LiveKit** | Real-time WebRTC voice chat (optional) | 7880 |
| **n8n** | Workflow automation (optional) | 5678 |
| **Qdrant** | Vector database for RAG (optional) | 6333 |
| **LiteLLM** | Multi-model API gateway (optional) | 4000 |

## Hardware Tiers

The installer **automatically detects your GPU** and selects the right configuration:

| Tier | VRAM | Model | Context | Example GPUs |
|------|------|-------|---------|--------------|
| 1 (Entry) | <12GB | Qwen2.5-7B | 8K | RTX 3080, RTX 4070 |
| 2 (Prosumer) | 12-20GB | Qwen2.5-14B-AWQ | 16K | RTX 3090, RTX 4080 |
| 3 (Pro) | 20-40GB | Qwen2.5-32B-AWQ | 32K | RTX 4090, A6000 |
| 4 (Enterprise) | 40GB+ | Qwen2.5-72B-AWQ | 32K | A100, H100, multi-GPU |

Override with: `./install.sh --tier 3`

See [docs/HARDWARE-GUIDE.md](docs/HARDWARE-GUIDE.md) for buying recommendations.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Open WebUI                    │
│               (localhost:3000)                  │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                     vLLM                        │
│           (localhost:8000/v1/...)               │
│         Qwen2.5-32B-Instruct-AWQ               │
└─────────────────────────────────────────────────┘
         │                              │
┌────────▼────────┐            ┌───────▼────────┐
│    Whisper      │            │     Kokoro      │
│ (STT :9000)     │            │ (TTS :8880)     │
└─────────────────┘            └────────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ n8n (:5678) │  │Qdrant(:6333)│  │LiteLLM(:4K) │
│  Workflows  │  │  Vector DB  │  │ API Gateway │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Optional Profiles

Enable components with Docker Compose profiles:

```bash
# Voice (STT + TTS)
docker compose --profile voice up -d

# Workflows (n8n)
docker compose --profile workflows up -d

# RAG (Qdrant + embeddings)
docker compose --profile rag up -d

# LiveKit Voice Chat (real-time WebRTC voice)
docker compose --profile livekit --profile voice up -d

# Everything
docker compose --profile voice --profile workflows --profile rag --profile livekit up -d
```

### LiveKit Voice Chat

Real-time voice conversation with your local AI:

1. Enable the profile: `docker compose --profile livekit --profile voice up -d`
2. Open http://localhost:7880 for LiveKit playground
3. Or integrate with any LiveKit-compatible client

**What it does:**
- WebRTC voice streaming (low latency)
- Whisper STT → Local LLM → Kokoro TTS pipeline
- Works with browser, mobile apps, or custom clients

See `agents/voice/` for the agent implementation.

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
LLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ  # Model (auto-set by installer)
MAX_CONTEXT=8192                          # Context window
GPU_UTIL=0.9                              # VRAM allocation (0.0-1.0)
```

## Showcase & Demos

```bash
# Interactive showcase (requires running services)
./scripts/showcase.sh

# Offline demo mode (no GPU/services needed)
./scripts/demo-offline.sh

# Run integration tests
./tests/integration-test.sh
```

## Useful Commands

```bash
cd ~/dream-server
docker compose ps                # Check status
docker compose logs -f vllm      # Watch vLLM logs
docker compose restart           # Restart services
docker compose down              # Stop everything
./status.sh                      # Health check all services
```

## Comparison

| Feature | Dream Server | Ollama + WebUI | LocalAI |
|---------|:---:|:---:|:---:|
| Full-stack one-command install | **LLM + voice + workflows + RAG + privacy** | LLM + chat only | LLM only |
| Hardware auto-detect + model selection | **Yes** | No | No |
| Voice agents (STT + TTS + WebRTC) | **Built in** | No | Limited |
| Inference engine | **vLLM** (continuous batching) | llama.cpp | llama.cpp |
| Workflow automation | **n8n (400+ integrations)** | No | No |
| PII redaction / privacy tools | **Built in** | No | No |
| Multi-GPU | **Yes** | Partial | Partial |

---

## Troubleshooting FAQ

**vLLM won't start / OOM errors**
- Reduce `MAX_CONTEXT` in `.env` (try 4096)
- Lower `GPU_UTIL` to 0.85
- Use a smaller model: `./install.sh --tier 1`

**"Model not found" on first boot**
- First launch downloads the model (10-30 min depending on size)
- Watch progress: `docker compose logs -f vllm`

**Open WebUI shows "Connection error"**
- vLLM is still loading. Wait for health check to pass: `curl localhost:8000/health`

**Port already in use**
- Change ports in `.env` (e.g., `WEBUI_PORT=3001`)
- Or stop the conflicting service: `sudo lsof -i :3000`

**Docker permission denied**
- Add yourself to the docker group: `sudo usermod -aG docker $USER`
- Log out and back in for it to take effect

**WSL: GPU not detected**
- Install NVIDIA drivers on Windows (not inside WSL)
- Verify with `nvidia-smi` inside WSL
- Ensure Docker Desktop has WSL integration enabled

---

## Documentation

- [QUICKSTART.md](QUICKSTART.md) — Detailed setup guide
- [HARDWARE-GUIDE.md](docs/HARDWARE-GUIDE.md) — What to buy
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — Extended troubleshooting
- [SECURITY.md](SECURITY.md) — Security best practices
- [OPENCLAW-INTEGRATION.md](docs/OPENCLAW-INTEGRATION.md) — Connect OpenClaw agents
- [Workflows README](workflows/README.md) — Pre-built n8n workflows

## License

Apache 2.0 — Use it, modify it, sell it. Just don't blame us.

---

*Built by [The Collective](https://github.com/Light-Heart-Labs/Lighthouse-AI) — Android-17, Todd, and friends*
