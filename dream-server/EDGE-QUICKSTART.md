# Dream Server — Edge Quickstart

*For Raspberry Pi 5, Mac Mini, or any 8GB+ system without a dedicated GPU.*

---

## Requirements

- **RAM:** 8GB minimum (16GB recommended)
- **Storage:** 20GB free for models and data
- **Docker:** 24.0+ with Compose v2

### Platform-Specific Notes

| Platform | Notes |
|----------|-------|
| **Pi 5** | Use 8GB model. Active cooling required. NVMe recommended. |
| **Mac Mini M1** | Works out of box. Ollama uses Metal automatically. |
| **Mac Mini M2+** | Best performance. 16GB+ recommended for 7B models. |
| **Linux laptop** | CPU inference. Expect slower speeds. |
| **Windows** | Use WSL2 + Docker Desktop. |

---

## Quick Start (2 minutes)

```bash
# 1. Clone and enter
git clone https://github.com/Light-Heart-Labs/Lighthouse-AI.git
cd Lighthouse-AI/dream-server

# 2. Start core services
docker compose -f docker-compose.edge.yml up -d

# 3. Pull default model (Qwen2.5-3B)
docker compose -f docker-compose.edge.yml --profile bootstrap up

# 4. Open the UI
# → http://localhost:3000
```

---

## Model Selection

Edit `.env` or set `LLM_MODEL` before starting:

| Model | Size | RAM Needed | Speed | Quality |
|-------|------|------------|-------|---------|
| `qwen2.5:0.5b` | 0.5B | 4GB | ⚡ Fast | ⚠️ Basic |
| `qwen2.5:1.5b` | 1.5B | 6GB | ⚡ Fast | 🟡 OK |
| `qwen2.5:3b` | 3B | 8GB | 🟡 Medium | ✅ Good |
| `qwen2.5:7b` | 7B | 12GB | 🔴 Slower | ✅ Great |
| `llama3.2:3b` | 3B | 8GB | 🟡 Medium | ✅ Good |
| `phi3:mini` | 3.8B | 8GB | 🟡 Medium | ✅ Good |

**Pi 5 8GB:** Stick to 3B or smaller.
**Mac Mini 16GB:** Can run 7B comfortably.

---

## Enable Voice (Optional)

```bash
# Start with voice services
docker compose -f docker-compose.edge.yml --profile voice up -d

# Pull Whisper model (first run)
# This happens automatically on first transcription request
```

### Voice Configuration

| Setting | Default | Recommended |
|---------|---------|-------------|
| `WHISPER_MODEL` | `tiny` | `tiny` for Pi, `base` for Mac |
| `PIPER_VOICE` | `en_US-lessac-medium` | Change for different accents |

---

## Enable Workflows (Optional)

```bash
# Start with n8n
docker compose -f docker-compose.edge.yml --profile workflows up -d

# Open n8n
# → http://localhost:5678
```

---

## Ports Reference

| Service | Port | URL |
|---------|------|-----|
| Open WebUI | 3000 | http://localhost:3000 |
| Ollama API | 11434 | http://localhost:11434 |
| Whisper STT | 9000 | http://localhost:9000 |
| Kokoro TTS | 8880 | http://localhost:8880 |
| n8n | 5678 | http://localhost:5678 |

---

## Performance Expectations

### Raspberry Pi 5 (8GB)

| Model | Tokens/sec | Voice Latency |
|-------|------------|---------------|
| Qwen2.5-0.5B | 25-30 t/s | 2s |
| Qwen2.5-1.5B | 12-15 t/s | 3s |
| Qwen2.5-3B | 4-6 t/s | 5s |

### Mac Mini M1 (8GB)

| Model | Tokens/sec | Voice Latency |
|-------|------------|---------------|
| Qwen2.5-3B | 15-20 t/s | 1.5s |
| Qwen2.5-7B | 8-12 t/s | 2.5s |

### Mac Mini M2 (16GB)

| Model | Tokens/sec | Voice Latency |
|-------|------------|---------------|
| Qwen2.5-7B | 20-30 t/s | 1s |
| Llama 3.2 8B | 18-25 t/s | 1.2s |

---

## Troubleshooting

### "Model too large" / OOM

Reduce model size or increase swap:
```bash
# Increase swap (Linux/Pi)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Slow on Pi 5

1. Ensure active cooling is working
2. Use NVMe instead of SD card
3. Reduce model size to 1.5B or 0.5B

### Ollama won't start on Mac

```bash
# Check if native Ollama is running
killall ollama

# Or use native Ollama instead of Docker
brew install ollama
ollama serve &
```

---

## Upgrading

```bash
# Pull latest images
docker compose -f docker-compose.edge.yml pull

# Restart
docker compose -f docker-compose.edge.yml up -d
```

---

## Next Steps

- Configure voice assistant: See `docs/VOICE-SETUP.md`
- Add OpenClaw agent: See `docs/OPENCLAW-INTEGRATION.md`
- Create automations: Use n8n at http://localhost:5678

---

*Part of the Dream Server project — Mission 5 (Dream Server) + Mission 6 (Min Hardware)*
