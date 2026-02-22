# Dream Server E2E Test Checklist

End-to-end validation checklist for testing the Dream Server installer (`install.sh`) on a fresh machine.

---

## 1. Pre-Test Machine Requirements

### Minimum System Requirements by Tier

| Tier | RAM | GPU | VRAM | Disk | Network |
|------|-----|-----|------|------|---------|
| **Nano** | 8GB+ | None | N/A | 20GB | Required |
| **Edge** | 16GB+ | NVIDIA | 8GB+ | 50GB | Required |
| **Pro** | 32GB+ | NVIDIA | 24GB+ | 80GB | Required |
| **Cluster** | 64GB+ | Multi-NVIDIA | 48GB+ | 200GB | Required |

### Pre-Test Checklist

- [ ] **Fresh OS installation** (Ubuntu 22.04/24.04 LTS recommended)
- [ ] **Root or sudo access** available
- [ ] **Internet connection** active (for image pulls)
- [ ] **No Docker installed** (to test install flow) OR **Docker installed but stopped**
- [ ] **No conflicting ports** in use (3001, 3002, 7880, 8000, 9000, 8880)
- [ ] **NVIDIA drivers installed** (Edge/Pro/Cluster tiers only)
  - [ ] Verify: `nvidia-smi` returns GPU info
  - [ ] Driver version ≥ 525.x
- [ ] **Clean home directory** (no `~/dream-server` folder)
- [ ] **Note baseline disk usage** for post-install comparison

---

## 2. Step-by-Step Test Procedure

### Phase 1: Pre-Installation Verification

- [ ] **Record system specs**
  ```bash
  uname -a
  cat /etc/os-release
  free -h
  nvidia-smi  # GPU tiers only
  df -h
  ```

- [ ] **Verify ports are free**
  ```bash
  ss -tlnp | grep -E ':(3001|3002|7880|8000|9000|8880)'
  ```

### Phase 2: Run Installer

- [ ] **Execute setup script**
  ```bash
  curl -fsSL https://raw.githubusercontent.com/Light-Heart-Labs/Lighthouse-AI/main/dream-server/get-dream-server.sh | bash
  ```
  OR for local testing:
  ```bash
  ./install.sh
  ```

- [ ] **Verify banner displays** correctly (ASCII art visible)

- [ ] **Confirm hardware detection**
  - [ ] OS detected correctly
  - [ ] RAM value matches `free -h`
  - [ ] GPU type detected (nvidia/apple/amd/none)
  - [ ] VRAM value matches `nvidia-smi`
  - [ ] Disk space value reasonable

- [ ] **Verify tier recommendation** matches hardware
  - [ ] 8GB RAM, no GPU → Nano
  - [ ] 16GB RAM or 8GB VRAM → Edge
  - [ ] 24GB+ VRAM → Pro
  - [ ] Multi-GPU 20GB+ each → Cluster

- [ ] **Tier selection prompt works**
  - [ ] Can select recommended tier (Enter)
  - [ ] Can select different tier (1-4)

- [ ] **Docker installation** (if not present)
  - [ ] Installer prompts for Docker install
  - [ ] Docker installs successfully
  - [ ] User added to docker group

- [ ] **NVIDIA Container Toolkit check** (GPU tiers)
  - [ ] Toolkit detected or warning displayed
  - [ ] Installation link provided if missing

- [ ] **Installation directory prompt**
  - [ ] Default `~/dream-server` suggested
  - [ ] Custom path accepted if provided

- [ ] **Configuration saved**
  - [ ] `.env` file created in install directory
  - [ ] Contains correct tier, model, GPU info

- [ ] **Compose file downloaded/generated**
  - [ ] `docker-compose.yml` present

- [ ] **Images pulled successfully**
  - [ ] No network errors
  - [ ] All required images downloaded

- [ ] **Services started**
  - [ ] `docker compose up -d` completes without error

### Phase 3: Post-Installation

- [ ] **Verify installation completed** (success message displayed)
- [ ] **Dashboard URL shown** (http://localhost:3001)
- [ ] **API URL shown** (http://localhost:8000/v1)
- [ ] **Next steps displayed**

---

## 3. Validation Points for Each Service

### All Tiers: Core Services

#### Dashboard (Port 3001)
- [ ] **HTTP accessible**: `curl -f http://localhost:3001`
- [ ] **Page loads** in browser
- [ ] **No JavaScript errors** in console
- [ ] **Container healthy**: `docker inspect dream-dashboard --format='{{.State.Health.Status}}'`

#### Dashboard API (Port 3002)
- [ ] **Health endpoint**: `curl -f http://localhost:3002/health`
- [ ] **Returns JSON** with status info
- [ ] **Container running**: `docker ps | grep dream-api`

### Nano Tier Services

#### LLaMA.cpp Server (Port 8000)
- [ ] **Health check**: `curl -f http://localhost:8000/health`
- [ ] **Model loaded**: Check logs for "model loaded"
  ```bash
  docker logs dream-llama 2>&1 | grep -i "model"
  ```
- [ ] **Chat completion works**:
  ```bash
  curl http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"Say hello"}]}'
  ```
- [ ] **Response is coherent** (not gibberish)

### Edge/Pro Tier Services

#### vLLM (Port 8000)
- [ ] **Health check**: `curl -f http://localhost:8000/health`
- [ ] **Model info endpoint**: `curl http://localhost:8000/v1/models`
- [ ] **Model name correct** in response
- [ ] **Chat completion works**:
  ```bash
  curl http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hello"}]}'
  ```
- [ ] **Streaming works** (add `"stream": true`)
- [ ] **GPU utilization visible**: `nvidia-smi` shows memory usage

#### Whisper STT (Port 9000)
- [ ] **Health check**: `curl -f http://localhost:9000/health`
- [ ] **Model loaded**: Check for model in logs
- [ ] **Transcription test**:
  ```bash
  # Create test audio or use sample
  curl -X POST http://localhost:9000/v1/audio/transcriptions \
    -F "file=@test.wav"
  ```
- [ ] **Returns text** transcription

#### Kokoro TTS (Port 8880)
- [ ] **Health check**: `curl -f http://localhost:8880/health`
- [ ] **Voices endpoint**: `curl http://localhost:8880/v1/audio/voices`
- [ ] **Speech generation**:
  ```bash
  curl -X POST http://localhost:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"input":"Hello world","voice":"af_heart"}' \
    --output test.mp3
  ```
- [ ] **Audio file plays** correctly

#### LiveKit (Port 7880)
- [ ] **HTTP accessible**: `curl -f http://localhost:7880`
- [ ] **WebSocket port open**: `nc -zv localhost 7880`
- [ ] **RTC port open**: `nc -zvu localhost 7882`

#### Voice Agent
- [ ] **Container running**: `docker ps | grep dream-voice-agent`
- [ ] **Connected to LiveKit**: Check logs for connection success
- [ ] **End-to-end voice test**: Use dashboard voice feature

### Cluster Tier Additional

#### Multi-GPU Validation
- [ ] **All GPUs visible**: `nvidia-smi` shows all GPUs
- [ ] **vLLM using multiple GPUs**: Check memory on each GPU
- [ ] **Tensor parallel configured**: Logs show TP value

---

## 4. Common Failure Scenarios and Fixes

### Installation Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `permission denied` on docker | User not in docker group | `sudo usermod -aG docker $USER` then re-login |
| `docker: command not found` | Docker not installed | Re-run installer or install manually |
| `nvidia-smi not found` | NVIDIA drivers missing | Install drivers: `sudo apt install nvidia-driver-535` |
| `could not select device driver` | NVIDIA Container Toolkit missing | Install: `apt install nvidia-container-toolkit` |
| `port already in use` | Conflicting service | Stop conflicting service or change port in .env |
| `no space left on device` | Disk full | Free space or use different mount point |
| `network timeout` pulling images | Slow/blocked network | Use VPN or configure Docker mirrors |

### Runtime Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| vLLM OOM crash | Model too large for VRAM | Choose smaller tier or reduce `--max-model-len` |
| Dashboard shows "Connection refused" | API service down | `docker compose restart api` |
| Whisper returns empty transcription | Model not loaded | Wait for model download, check logs |
| TTS generates silence | Voice model missing | Check Kokoro logs, ensure cache volume mounted |
| Voice agent not responding | Service dependencies not healthy | Restart in order: vllm → whisper → kokoro → voice-agent |
| `CUDA out of memory` | Multiple GPU services competing | Stagger service startup, reduce batch sizes |

### Service Health Issues

| Service | Health Check | Recovery Command |
|---------|--------------|------------------|
| vLLM | `curl localhost:8000/health` | `docker compose restart vllm` |
| Whisper | `curl localhost:9000/health` | `docker compose restart whisper` |
| Kokoro | `curl localhost:8880/health` | `docker compose restart kokoro` |
| LiveKit | `curl localhost:7880` | `docker compose restart livekit` |
| Dashboard | `curl localhost:3001` | `docker compose restart dashboard` |

### Debug Commands

```bash
# View all service logs
docker compose logs -f

# Check specific service
docker compose logs -f vllm

# Check resource usage
docker stats

# Inspect container health
docker inspect <container> --format='{{json .State.Health}}'

# Force recreate all services
docker compose down && docker compose up -d

# Nuclear option: full reset
docker compose down -v
rm -rf ./data ./models
docker compose up -d
```

---

## 5. Success Criteria

### Installation Success

- [ ] **Installer completes** without errors (exit code 0)
- [ ] **All containers running**: `docker compose ps` shows all "Up"
- [ ] **No containers restarting**: No "Restarting" status after 5 minutes
- [ ] **.env file created** with correct configuration
- [ ] **Data directories created**: `./data`, `./models` exist

### Service Health Success

- [ ] **All health checks pass** (see Section 3)
- [ ] **No error logs** in past 5 minutes: `docker compose logs --since 5m | grep -i error`
- [ ] **Memory usage stable**: `docker stats` shows no memory climb

### Functional Success

- [ ] **Dashboard loads** in browser at http://localhost:3001
- [ ] **Chat works**: Can send message and receive response
- [ ] **Response quality**: LLM generates coherent, relevant text
- [ ] **Voice works** (Edge/Pro/Cluster): Can speak and get voice response
- [ ] **Latency acceptable**: 
  - Text response: < 5s for first token
  - Voice response: < 2s for first audio

### Performance Benchmarks (Optional)

| Metric | Nano | Edge | Pro | Cluster |
|--------|------|------|-----|---------|
| Tokens/sec | > 10 | > 30 | > 50 | > 80 |
| First token latency | < 2s | < 1s | < 1s | < 1s |
| STT latency | N/A | < 500ms | < 300ms | < 200ms |
| TTS latency | N/A | < 1s | < 500ms | < 300ms |

### Final Checklist

- [ ] **All services healthy** for 10+ minutes
- [ ] **Completed test conversation** (5+ exchanges)
- [ ] **Voice round-trip works** (Edge/Pro/Cluster)
- [ ] **No unexpected errors** in logs
- [ ] **Disk usage reasonable** (model size + 10GB overhead)
- [ ] **GPU memory stable** (not climbing)

---

## Test Report Template

```markdown
## Dream Server E2E Test Report

**Date:** YYYY-MM-DD
**Tester:** 
**Machine:** 

### System Specs
- OS: 
- RAM: 
- GPU: 
- VRAM: 
- Disk: 

### Tier Tested
- [ ] Nano
- [ ] Edge
- [ ] Pro
- [ ] Cluster

### Results
- Installation: PASS / FAIL
- Services Healthy: PASS / FAIL
- Chat Functional: PASS / FAIL
- Voice Functional: PASS / FAIL / N/A

### Issues Found
1. 
2. 

### Notes

```

---

*Last updated: 2026-02-10*
