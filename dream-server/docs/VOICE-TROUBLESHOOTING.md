# Voice Workflow Troubleshooting Guide

*Troubleshooting guide for Dream Server voice deployments*

---

## Quick Diagnosis

```bash
# Check all voice services at once
curl -s http://localhost:9101/health  # Whisper STT
curl -s http://localhost:8880/api/voices  # OpenTTS
curl -s http://localhost:8000/health  # vLLM

# Check Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## Problem 1: Whisper Not Transcribing

### Symptoms
- Audio uploads timeout
- Empty transcription results
- "Connection refused" on port 9101

### Diagnosis Commands
```bash
# Check if Whisper is running
docker ps | grep whisper

# Check Whisper logs
docker logs whisper-stt 2>&1 | tail -50

# Test Whisper endpoint directly
curl -X POST http://localhost:9101/transcribe \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@test.wav"
```

### Common Fixes

**Container not running:**
```bash
cd ~/dream-server && docker compose up -d whisper
```

**Wrong port configured:**
```bash
# Check .env file
grep WHISPER_PORT .env
# Should be: WHISPER_PORT=9101

# Restart with correct port
docker compose down whisper && docker compose up -d whisper
```

**Out of memory:**
```bash
# Check GPU memory
nvidia-smi

# If OOM, switch to smaller Whisper model
# Edit .env: WHISPER_MODEL=base (instead of medium/large)
docker compose down whisper && docker compose up -d whisper
```

**Model not downloaded:**
```bash
docker logs whisper-stt 2>&1 | grep -i "downloading"
# Wait for download to complete, then retry
```

---

## Problem 2: TTS Not Generating Audio

### Symptoms
- No audio output from voice agents
- Empty responses from TTS endpoint
- "Service unavailable" errors

### Diagnosis Commands

**For OpenTTS (port 8880):**
```bash
# Check if running
docker ps | grep opentts

# List available voices
curl http://localhost:8880/api/voices

# Test TTS generation
curl "http://localhost:8880/api/tts?text=Hello%20world&voice=larynx:en-us/harvard-glow_tts" \
  --output test.wav
```

**For Piper (port 10200):**
```bash
# Check if running
docker ps | grep piper

# Test Piper directly
curl -X POST http://localhost:10200/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "en_US-lessac-medium"}' \
  --output test.wav
```

**For Kokoro (port 9102):**
```bash
# Check if running
docker ps | grep kokoro

# Test Kokoro
curl -X POST http://localhost:9102/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}' \
  --output test.wav
```

### Common Fixes

**Port mismatch between install.sh and docker-compose:**
```bash
# Verify which TTS is configured
grep -E "(PIPER_PORT|TTS_PORT)" .env

# OpenTTS should be 8880
# Piper should be 10200
# Kokoro should be 9102
```

**Voice model not downloaded:**
```bash
# Check TTS logs for download status
docker logs opentts 2>&1 | tail -50

# For Piper, ensure voice pack exists
docker exec piper-tts ls /voices/
```

**Wrong TTS configured in web UI:**
1. Open WebUI settings → Audio
2. Verify TTS URL matches your running service
3. OpenTTS: `http://localhost:8880/api/tts`
4. Piper: `http://localhost:10200/api/tts`

---

## Problem 3: High Latency (Slow Responses)

### Symptoms
- Voice agent takes >3 seconds to respond
- Audio plays choppy or delayed
- Users report "lag"

### Diagnosis Commands
```bash
# Check GPU utilization
nvidia-smi -l 1

# Check vLLM queue depth
curl http://localhost:8000/metrics | grep vllm_request

# Profile a full round-trip
time curl -X POST http://localhost:9101/transcribe -F "audio=@test.wav"
time curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-32B-AWQ","messages":[{"role":"user","content":"Hi"}]}'
time curl "http://localhost:8880/api/tts?text=Hello&voice=larynx:en-us/harvard-glow_tts" -o /dev/null
```

### Common Fixes

**GPU at 100%:**
```bash
# Check what's using GPU
nvidia-smi

# Consider smaller model
# Edit .env: LLM_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ (instead of 32B)
docker compose down vllm && docker compose up -d vllm
```

**Too many concurrent users:**
```bash
# Check active connections
docker logs vllm 2>&1 | grep "requests"

# Add rate limiting or scale up
```

**Whisper model too large:**
```bash
# Use base or small for faster inference
# Edit .env: WHISPER_MODEL=base
docker compose down whisper && docker compose up -d whisper
```

**Network buffering issues:**
```bash
# For LiveKit, check latency settings
grep -i buffer prototypes/grace-livekit/agent.py

# Reduce buffer sizes if latency is more important than stability
```

---

## Problem 4: Voice Agent Not Responding

### Symptoms
- Agent receives audio but doesn't answer
- Intent classifier returns wrong intent
- FSM gets stuck

### Diagnosis Commands
```bash
# Check intent classifier
curl -X POST http://localhost:8080/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Schedule an appointment for tomorrow"}'

# Check FSM state
cat tools/deterministic-voice/state.json

# Check agent logs
docker logs grace-agent 2>&1 | tail -100
```

### Common Fixes

**Intent classifier not running:**
```bash
cd tools/intent-classifier
python -m uvicorn api:app --host 0.0.0.0 --port 8080
```

**FSM stuck in wrong state:**
```bash
# Reset FSM state
echo '{"state": "idle"}' > tools/deterministic-voice/state.json

# Or restart the agent
docker compose restart grace-agent
```

**Model loading failed:**
```bash
# Check if classifier model exists
ls tools/intent-classifier/models/

# If missing, retrain
cd tools/intent-classifier && python train.py
```

---

## Problem 5: LiveKit Connection Problems

### Symptoms
- WebRTC connection fails
- "Room not found" errors
- Audio/video black screen

### Diagnosis Commands
```bash
# Check LiveKit status
curl http://localhost:7880/

# Check LiveKit logs
docker logs livekit 2>&1 | tail -50

# Check ports are accessible
netstat -tlnp | grep -E "(7880|7881|7882)"
```

### Common Fixes

**LiveKit not running:**
```bash
docker compose up -d livekit
```

**Firewall blocking WebRTC:**
```bash
# Allow WebRTC ports
sudo ufw allow 7880/tcp  # HTTP
sudo ufw allow 7881/tcp  # RTMP (optional)
sudo ufw allow 50000:60000/udp  # WebRTC media
```

**SSL/TLS issues (production):**
```bash
# For local testing, use ws:// not wss://
# For production, ensure valid SSL cert on LiveKit

# Check cloudflared tunnel if using
docker logs cloudflared 2>&1 | grep livekit
```

**Room doesn't exist:**
```bash
# Create room first
curl -X POST http://localhost:7880/twirp/livekit.RoomService/CreateRoom \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LIVEKIT_API_KEY" \
  -d '{"name": "test-room"}'
```

---

## Service Status Quick Check

Run this to check all voice services:

```bash
#!/bin/bash
echo "=== Voice Service Status ==="
echo ""

# vLLM
echo -n "vLLM (8000): "
curl -s http://localhost:8000/health && echo "✅ OK" || echo "❌ DOWN"

# Whisper
echo -n "Whisper (9101): "
curl -s http://localhost:9101/health && echo "✅ OK" || echo "❌ DOWN"

# OpenTTS
echo -n "OpenTTS (8880): "
curl -s http://localhost:8880/api/voices > /dev/null && echo "✅ OK" || echo "❌ DOWN"

# LiveKit
echo -n "LiveKit (7880): "
curl -s http://localhost:7880/ > /dev/null && echo "✅ OK" || echo "❌ DOWN"

echo ""
echo "=== GPU Status ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
```

Save as `check-voice.sh` and run: `bash check-voice.sh`

---

## Getting Help

1. Check logs: `docker logs <service-name> 2>&1 | tail -100`
2. Restart service: `docker compose restart <service-name>`
3. Full reset: `docker compose down && docker compose up -d`
4. GitHub Issues: https://github.com/Light-Heart-Labs/Lighthouse-AI/issues
5. Discord community (link in README)

---

*Part of Dream Server M5 documentation*
