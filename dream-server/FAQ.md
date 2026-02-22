# Dream Server FAQ

Frequently asked questions about installing, running, and troubleshooting Dream Server.

> **Also see:** [`docs/FAQ.md`](docs/FAQ.md) for hardware requirements, pricing, and comparisons with alternatives.

---

## General Questions

### What is Dream Server?
Dream Server is a turnkey local AI stack that runs entirely on your own hardware. It includes:
- LLM inference via vLLM (Qwen2.5-32B-Instruct-AWQ)
- Web dashboard for chat and model management
- Voice capabilities (STT via Whisper, TTS via Kokoro)
- Workflow automation via n8n
- API gateway with privacy shield for external services

### What are the minimum requirements?
**Minimum (bootstrap mode):**
- Any modern CPU
- 8GB RAM
- 10GB disk space
- Docker + Docker Compose

**Recommended (full experience):**
- NVIDIA GPU with 24GB+ VRAM (RTX 3090/4090)
- 32GB+ system RAM
- 100GB+ SSD storage
- Ubuntu 22.04/24.04 or WSL2 on Windows

### Do I need an internet connection?
**Initial setup:** Yes, to download models and Docker images.

**After setup:** No. Dream Server is designed for offline/air-gapped operation. All models run locally.

### Is my data private?
Yes. Everything runs on your hardware:
- Conversations never leave your machine
- Voice processing is local
- API calls to external services go through the Privacy Shield (PII redaction)
- No telemetry or analytics

### How much does it cost?
Dream Server is **free and open source** (Apache 2.0 license). You only pay for:
- Your hardware (one-time cost)
- Electricity to run it

---

## Installation

### The installer fails with "Docker not found"
**Linux:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

**Windows:**
Install Docker Desktop from https://docs.docker.com/desktop/install/windows-install/
Enable WSL2 backend in Docker Desktop settings.

### "Permission denied" when running install.sh
Make the script executable:
```bash
chmod +x install.sh
./install.sh
```

### The installer hangs during model download
This is normal for large models (20GB+). The installer shows progress bars with:
- Download speed
- Time elapsed
- ETA

**To speed up:** Use a wired connection. WiFi can be unstable for large downloads.

**To restart:** The installer resumes partial downloads automatically.

### Bootstrap mode started but I want the full model now
```bash
./scripts/upgrade-model.sh
```

This hot-swaps from the 1.5B bootstrap model to your full model without downtime.

### How do I skip bootstrap mode?
```bash
./install.sh --no-bootstrap
```

This downloads the full model first. You'll wait longer before first use.

### NVIDIA GPU not detected
**Check driver:**
```bash
nvidia-smi
```

**If missing:** Install NVIDIA drivers:
```bash
# Ubuntu
sudo apt update
sudo apt install nvidia-driver-550
sudo reboot
```

**Check Docker runtime:**
```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### "CUDA out of memory" errors
Your GPU doesn't have enough VRAM. Options:
1. Use a smaller model (Qwen2.5-7B instead of 32B)
2. Enable quantization (AWQ format uses ~60% less VRAM)
3. Reduce `max_model_len` in docker-compose.yml
4. Run on CPU only (slower but works)

### Windows: WSL2 installation fails
Enable WSL2 manually:
```powershell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
```

Then restart the installer.

### The web dashboard won't load
**Check if services are running:**
```bash
docker compose ps
```

**Check logs:**
```bash
docker compose logs dashboard-api
docker compose logs vllm
```

**Common fixes:**
- Wait 30 seconds for services to start
- Check http://localhost:3001 (direct API) vs http://localhost:3000 (UI)
- Restart: `docker compose restart`

### How do I uninstall?
```bash
docker compose down -v  # Stop and remove containers + volumes
rm -rf ~/dream-server    # Remove installation directory (optional)
```

This removes Docker containers and volumes. Add `-v` to also remove downloaded models and data.

---

## Usage

### How do I access the web interface?
```
http://localhost:3000
```

On first run, the installer displays a QR code. Scan it with your phone for instant mobile access.

### What's the default password?
The installer generates secure random passwords and displays them at the end. Look for:
```
✓ Dashboard URL: http://localhost:3000
✓ API Key: dsf8a9s7df8a9s7df...
```

Passwords are also saved to `.env` in the dream-server directory.

### How do I change the password?
Edit `.env`:
```bash
nano .env
# Change: DASHBOARD_PASSWORD=your-new-password
docker compose restart dashboard
```

### Can I access from other devices on my network?
Yes! Use your machine's local IP:
```
http://192.168.1.xxx:3000
```

The installer shows this URL with a QR code at the end.

### How do I create a workflow?
1. Open http://localhost:3000/workflows
2. Click "New Workflow"
3. Select a template or start from scratch
4. Connect nodes (triggers → actions)
5. Save and activate

### What's n8n?
n8n is the workflow engine built into Dream Server. It provides:
- Visual workflow editor
- 400+ integrations (GitHub, Slack, email, etc.)
- Webhook triggers
- Scheduled jobs
- AI agent capabilities

### Can I connect to external APIs?
Yes, through the **Privacy Shield**:
1. Configure the shield service (runs on port 8085)
2. Route API calls through `http://localhost:8085/proxy/{service}`
3. PII is automatically redacted before leaving your network

### How do I use voice features?
**Prerequisites:** Microphone and speakers/headphones

1. Open the Voice page in the dashboard
2. Click "Start Conversation"
3. Allow microphone access
4. Speak naturally — the system handles STT → LLM → TTS automatically

### Which STT model should I use?
| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| tiny | ~400ms | Good | Quick commands |
| base | ~700ms | Better | General use |
| small | ~2s | Best | Accuracy critical |
| large-v3 | ~8s | Excellent | Offline transcription |

Default is `base`. Change in Settings → Voice.

### Which TTS voice is best?
Kokoro provides high-quality voices. Options:
- `af_bella` — Natural female (default)
- `af_nicole` — Professional female
- `am_adam` — Natural male
- `am_michael` — Professional male

Preview voices in Settings → Voice → Test.

---

## Troubleshooting

### Where are the logs?
**All services:**
```bash
docker compose logs -f
```

**Specific service:**
```bash
docker compose logs -f vllm
docker compose logs -f dashboard-api
docker compose logs -f voice-agent
```

**To file:**
```bash
docker compose logs > dream-server.log 2>&1
```

### How do I restart everything?
```bash
docker compose down
docker compose up -d
```

Or restart specific services:
```bash
docker compose restart vllm
```

### "Connection refused" to API
1. Check if the API container is running: `docker compose ps dashboard-api`
2. Check logs: `docker compose logs dashboard-api`
3. Verify port 3001 is not in use: `sudo lsof -i :3001`
4. Restart: `docker compose restart dashboard-api`

### Models won't load
**Check disk space:**
```bash
df -h
```

Models need ~20GB per model. Free up space if needed.

**Check model download:**
```bash
ls -la models/
```

If empty or incomplete, re-download:
```bash
./scripts/pre-download.sh
```

### Voice quality is poor
**STT issues:**
- Check microphone input level
- Reduce background noise
- Try a different STT model (base → small)

**TTS issues:**
- Check speaker/headphone connection
- Adjust TTS speed in Settings
- Try different voices

### Slow response times
**Check GPU utilization:**
```bash
nvidia-smi
```

If GPU is at 100%, you're GPU-bound. Solutions:
- Reduce concurrent requests
- Use a smaller model
- Enable KV cache quantization

**Check if using CPU:**
If `nvidia-smi` shows no process, the model is running on CPU (very slow). Fix GPU detection issues above.

### "Rate limit exceeded" errors
The Privacy Shield has rate limiting to prevent abuse. Default: 100 requests/minute.

To increase:
1. Edit `privacy-shield-mvp-bundle/.env`
2. Change `RATE_LIMIT_REQUESTS_PER_MINUTE=100`
3. Restart: `docker compose restart privacy-shield`

### Workflows not triggering
**Check webhook URL:**
Must be accessible from the triggering service.

**Check n8n logs:**
```bash
docker compose logs n8n
```

**Verify workflow is active:**
In the workflow editor, toggle must be ON (green).

### Docker volumes taking too much space
Clean up unused volumes:
```bash
docker volume prune
```

Or remove everything (destructive):
```bash
docker compose down -v
```

---

## Advanced

### How do I add a custom model?
1. Download model to `models/` directory
2. Edit `docker-compose.yml` — change `LLM_MODEL` environment variable
3. Restart: `docker compose up -d vllm`

Supported formats: AWQ, GPTQ, EXL2, GGUF (via llama.cpp adapter)

### How do I enable HTTPS?
For production deployments, use a reverse proxy (nginx, Caddy, Traefik) in front of Dream Server:

```bash
# Example with Caddy (auto-HTTPS with Let's Encrypt)
caddy reverse-proxy --from your-domain.com --to localhost:3000
```

For local development, browsers accept self-signed certs at `https://localhost`.

### Can I run on multiple GPUs?
Yes! Edit `docker-compose.yml`:
```yaml
environment:
  - TENSOR_PARALLEL_SIZE=2  # Use 2 GPUs
  - GPU_MEMORY_UTILIZATION=0.95
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 2  # Number of GPUs
          capabilities: [gpu]
```

### How do I backup my data?
**Configs and workflows:**
```bash
tar -czf dream-server-backup.tar.gz .env workflows/ n8n-data/
```

**Models (large):**
```bash
rsync -av models/ /backup/location/models/
```

### How do I update Dream Server?
```bash
./dream-update.sh
```

Or manually:
```bash
git pull
docker compose pull
docker compose up -d
```

This pulls latest code, updates Docker images, and migrates data.

### Where is the database?
SQLite databases are in Docker volumes:
- `dream-server_n8n-data` — Workflows and credentials
- `dream-server_agent-monitor` — Metrics and logs

Access via:
```bash
docker compose exec n8n sqlite3 /home/node/.n8n/database.sqlite
```

### Can I use OpenAI/Anthropic APIs?
Yes, through the Privacy Shield. Configure in Settings → API Keys.

Your requests go: You → Shield (PII redaction) → OpenAI → Shield (deanonymization) → You

### How do I monitor performance?
Open the Dashboard → Metrics page for:
- GPU utilization and temperature
- Request latency (P50, P95, P99)
- Token throughput
- Active connections

Or use the API:
```bash
curl http://localhost:3001/api/metrics
```

### What ports are used?
| Port | Service |
|------|---------|
| 3000 | Open WebUI (chat interface) |
| 3001 | Dashboard |
| 3002 | Dashboard API |
| 8000 | vLLM API |
| 8085 | Privacy Shield |
| 5678 | n8n workflow editor |
| 7880 | LiveKit voice server |
| 9000 | Whisper STT |
| 8880 | Kokoro TTS |
| 6333 | Qdrant vector DB |
| 8090 | Embeddings service |

### How do I change the port?
Edit `.env`:
```bash
DASHBOARD_PORT=8080
```

Then restart: `docker compose up -d`

---

## Getting Help

### Documentation
- Main README: `dream-server/README.md`
- Architecture: `docs/ARCHITECTURE.md`
- API Reference: `docs/API.md`

### Community
- GitHub Issues: https://github.com/Light-Heart-Labs/Lighthouse-AI/issues
- Discord: #general channel

### Debug info for bug reports
Include this output:
```bash
# Collect system info
echo "=== Docker Compose ===" && docker compose version
echo "=== Services ===" && docker compose ps
echo "=== Recent Logs ===" && docker compose logs --tail=50
echo "=== GPU ===" && nvidia-smi 2>/dev/null || echo "No GPU"
```

Copy the output into your GitHub issue.

---

*Last updated: 2026-02-11*
