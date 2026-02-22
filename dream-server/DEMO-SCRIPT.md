# Dream Server Client Demo Script

## Overview
This script guides you through a hands-on demo of Dream Server. The demo covers hardware detection, local LLM chat, voice capabilities, and workflow automation.

**Prerequisites:** Dream Server installed and running (`./scripts/validate.sh` shows green)

---

## 1. Hardware Overview

**Talking Points:**
- Show the auto-detected hardware tier
- Explain how Dream Server optimizes for available resources

**Commands:**
```bash
# Show GPU info
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Check what tier Dream Server detected
cat .env | grep -E "LLM_MODEL|MAX_CONTEXT"
```

**Expected Output:**
GPU model and VRAM, plus the model/context settings Dream Server chose.

---

## 2. Local LLM Chat

**Talking Points:**
- Fully local inference — data never leaves the machine
- OpenAI-compatible API — drop-in replacement for existing tools

**Commands:**
```bash
# Chat completion via API
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [{"role": "user", "content": "What is Dream Server in one sentence?"}],
    "max_tokens": 100
  }' | jq '.choices[0].message.content'
```

**Expected Output:**
A coherent response from the local Qwen model (1-3 seconds).

**Then:** Open http://localhost:3000 to show the chat UI.

---

## 3. Voice Capabilities (if enabled)

**Talking Points:**
- Speech-to-text with Whisper
- Text-to-speech with Kokoro
- Full voice-to-voice conversations via LiveKit

**Commands:**
```bash
# Check voice services are running
docker compose ps whisper piper

# Test STT (if you have an audio file)
curl -X POST "http://localhost:9000/asr" \
  -F "audio_file=@test.wav" \
  -F "output=json"
```

**Then:** If LiveKit is enabled, open http://localhost:7880 for the voice playground.

---

## 4. Workflow Automation with n8n

**Talking Points:**
- Visual workflow builder
- Pre-built workflows for chat, RAG, voice transcription
- Integrates with any API

**Commands:**
```bash
# Check n8n is running
curl -s http://localhost:5678/ | head -1
```

**Then:** Open http://localhost:5678 and show the pre-imported workflows.

---

## 5. RAG Document Q&A (if enabled)

**Talking Points:**
- Upload documents, ask questions
- Qdrant vector database for semantic search
- Answers cite their sources

**Commands:**
```bash
# Check RAG services
docker compose ps qdrant embeddings
```

**Demo flow:** Import the document-qa workflow in n8n, upload a PDF, ask questions.

---

## 6. The Numbers

**Talking Points:**
- **Cost:** $0/month after hardware (vs $15K+/month for 1M cloud requests)
- **Latency:** 1.5-2s for 32B model
- **Capacity:** 30-40 concurrent voice sessions on dual-GPU
- **Privacy:** Data never leaves your premises

---

## Conclusion

**Summary:**
- Full-featured AI stack: chat, voice, workflows, RAG
- Runs on hardware they already own (or can buy once)
- OpenAI-compatible API — existing tools just work
- Total data sovereignty

**Next Steps:**
- Hardware purchase guide: `docs/HARDWARE-GUIDE.md`
- Pricing tiers: `docs/PRICING-TIERS.md`
- Contact for install support

---

*Built by The Collective — Android-17, Todd, and friends*
