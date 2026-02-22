# 🚀 Dream Server — Stranger Test Guide

**Welcome, brave tester!** You're about to set up Dream Server — a turnkey local AI stack that runs entirely on your own hardware. No cloud, no subscriptions, no data leaving your machine.

This guide assumes you've never seen this project before. If something doesn't work, that's valuable feedback — we want to know!

---

## 📋 What You're Testing

Dream Server gives you:
- **Local LLM** — A powerful AI chatbot running on your GPU
- **Chat Interface** — Beautiful web UI at `localhost:3000`
- **Voice** (optional) — Speech-to-text and text-to-speech
- **Workflows** (optional) — Automation via n8n
- **RAG** (optional) — Document Q&A with vector search

**Your job:** Follow this guide, note any friction, and tell us what sucked.

---

## ⚡ Quick Requirements Check

Before you start, verify:

### Linux
- [ ] Docker installed (`docker --version`)
- [ ] Docker Compose v2+ (`docker compose version`)
- [ ] NVIDIA GPU with 8GB+ VRAM (`nvidia-smi`)
- [ ] NVIDIA Container Toolkit (`nvidia-container-cli --version`)
- [ ] 40GB+ free disk space (`df -h`)

### Windows
- [ ] Windows 10 21H2+ or Windows 11
- [ ] NVIDIA GPU with recent drivers
- [ ] Docker Desktop (installer will help if missing)
- [ ] 40GB+ free disk space

**Don't have something?** That's fine — the installer will tell you what's missing.

---

## 🎬 What to Expect on First Boot

Here's the honest timeline:

| Phase | Time | What's Happening |
|-------|------|------------------|
| Clone repo | 1-2 min | Downloading ~100MB of code |
| Run installer | 5-10 min | Interactive setup, config generation |
| Pull containers | 5-10 min | Downloading Docker images (~10GB) |
| Model download | 10-30 min | Downloading the LLM (10-25GB) |
| Ready! | — | Chat at localhost:3000 |

**Total:** 20-60 minutes depending on internet speed and hardware.

> ⚠️ **The model download is the longest part.** First boot downloads 10-25GB. It looks like nothing is happening, but it is. Watch with `docker compose logs -f vllm`.

---

## 🛠️ Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/Light-Heart-Labs/Lighthouse-AI.git
cd Lighthouse-AI/dream-server
```

### Step 2: Run the Installer

```bash
./install.sh
```

**What it does:**
1. Detects your GPU and picks the right model tier
2. Checks Docker and NVIDIA toolkit are working
3. Asks which optional features you want (voice, workflows, RAG)
4. Generates secure passwords and `.env` file
5. Starts all services

**Pro tip:** Just hit Enter to accept defaults if you're not sure.

### Step 3: Wait for Model Download

This is the part where you go make coffee. ☕

Watch progress with:
```bash
docker compose logs -f vllm
```

**Look for:** `Application startup complete` — that means it's ready!

### Step 4: Open the Chat UI

Go to: **http://localhost:3000**

1. Create an account (first user = admin)
2. Select a model from the dropdown
3. Ask it something!

---

## ✅ Verification Checklist

Use this to confirm each component is working:

### Core Services

| Component | How to Check | Expected Result |
|-----------|--------------|-----------------|
| **vLLM (AI Engine)** | `curl http://localhost:8000/health` | Returns `{"status":"healthy"}` or similar |
| **Open WebUI** | Open http://localhost:3000 | See login/signup page |
| **Chat Response** | Send a message in WebUI | Get an AI response back |

### Test vLLM Directly

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-32B-Instruct-AWQ", "messages": [{"role": "user", "content": "Say hello!"}]}'
```

Should return a JSON response with the AI's reply.

### Optional Services

If you enabled these during install:

| Component | Port | How to Check |
|-----------|------|--------------|
| **Whisper (STT)** | 9000 | `curl http://localhost:9000/` |
| **OpenTTS (TTS)** | 8880 | `curl http://localhost:8880/` |
| **n8n (Workflows)** | 5678 | Open http://localhost:5678 |
| **Qdrant (Vector DB)** | 6333 | `curl http://localhost:6333/` |
| **LiveKit (Voice Chat)** | 7880 | Open http://localhost:7880 |

### Quick Status Script

Run this for an instant health check:
```bash
./status.sh
```

You should see green checkmarks ✓ next to running services.

---

## 🔥 Common Issues and Fixes

### 😱 "Nothing is happening after install started"

**It's downloading the model.** This takes 10-30 minutes and shows no progress bar.

**Fix:** Watch the logs:
```bash
docker compose logs -f vllm
```

### 😵 "CUDA out of memory" or "OOM"

Your GPU doesn't have enough VRAM for the selected model.

**Fix:** Edit `.env` and reduce context:
```bash
MAX_CONTEXT=4096  # or try 2048
```

Or use a smaller model:
```bash
./install.sh --tier 1  # Forces smallest model
```

### 🤔 "WebUI says No Models Available"

vLLM is still loading. This takes 1-5 minutes after container starts.

**Fix:** Wait and refresh. Check progress:
```bash
docker compose logs -f vllm
# Look for "Application startup complete"
```

### 🔒 "Permission denied" (Docker)

You're not in the docker group.

**Fix:**
```bash
sudo usermod -aG docker $USER
# Log out and back in, then try again
```

### 🔌 "Port already in use"

Something else is using that port.

**Fix:** Find it and stop it:
```bash
lsof -i :3000  # See what's using port 3000
```

Or change the port in `.env`:
```bash
WEBUI_PORT=3001
```

Then restart:
```bash
docker compose down && docker compose up -d
```

### 🎮 "GPU not detected" (WSL/Windows)

NVIDIA drivers need to be on Windows, not in WSL.

**Fix:**
1. Install NVIDIA drivers on Windows (not inside WSL)
2. Run `nvidia-smi` in WSL — should show your GPU
3. Ensure Docker Desktop has "WSL 2 based engine" enabled
4. In Docker Desktop settings, enable WSL integration for your distro

### ⏱️ "Responses are very slow"

**Possible causes:**
- First request is always slow (model warming up)
- Model is too big for your GPU (check `nvidia-smi`)
- Context window is too large

**Fix:** Use `watch nvidia-smi` while chatting. If GPU memory is maxed out, reduce `MAX_CONTEXT` or use smaller model.

---

## 📝 Useful Commands

Keep these handy:

```bash
# Check what's running
docker compose ps

# Watch all logs
docker compose logs -f

# Watch specific service
docker compose logs -f vllm

# Restart everything
docker compose restart

# Stop everything
docker compose down

# Check GPU usage
nvidia-smi

# Check disk space
df -h

# Full status check
./status.sh
```

---

## 📣 Feedback Template

**Please copy this, fill it out, and send it back!**

```markdown
## Dream Server Test Feedback

**Tester:** [Your name/handle]
**Date:** [Date]
**Hardware:** [GPU model, RAM, OS]

### Installation Experience

**Time to complete:** [How long did install take?]
**Did you hit any errors?** [Yes/No — if yes, describe]
**Was anything confusing?** [What would you improve?]

### First Boot

**Did the model download?** [Yes/No — how long?]
**Did WebUI load?** [Yes/No]
**Did you get a chat response?** [Yes/No]

### Verification Results

| Component | Working? | Notes |
|-----------|----------|-------|
| vLLM API | ✓/✗ | |
| Open WebUI | ✓/✗ | |
| Chat works | ✓/✗ | |
| Whisper (if enabled) | ✓/✗ | |
| OpenTTS (if enabled) | ✓/✗ | |
| n8n (if enabled) | ✓/✗ | |

### Issues Encountered

1. [Describe any issues]
2. [And how you solved them, if you did]

### Documentation Gaps

**What wasn't explained that should be?**
[Free text]

**What was confusing in the docs?**
[Free text]

### Overall Rating

**Setup difficulty:** [1-5, 1=easy, 5=nightmare]
**Would you recommend this to a friend?** [Yes/No/Maybe]
**What would make this better?**
[Free text]

### Extra Notes

[Anything else you want to share]
```

---

## 🆘 If You're Truly Stuck

1. **Check the logs:** `docker compose logs -f` shows everything
2. **Read TROUBLESHOOTING.md:** More detailed solutions
3. **Reset and retry:**
   ```bash
   docker compose down -v
   rm -rf data/
   ./install.sh
   ```
4. **Open an issue:** https://github.com/Light-Heart-Labs/Lighthouse-AI/issues

---

## 🙏 Thank You!

Your feedback makes Dream Server better. Every friction point you report is one less person who gives up.

We're building this so anyone can run AI on their own hardware. You're helping make that real.

— *The Collective (Android-17, Todd, and friends)*

---

*Document version: 2026-02-10 | Dream Server v0.1*
