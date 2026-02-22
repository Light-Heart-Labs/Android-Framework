# Dream Server Windows Quickstart

Get Dream Server running on Windows in 5 minutes (after downloads).

---

## One-Line Install (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Light-Heart-Labs/Lighthouse-AI/main/dream-server/install.ps1" -OutFile install.ps1; .\install.ps1
```

**Prerequisites:** Windows 10 2004+ or Windows 11, NVIDIA GPU, 16GB+ RAM.

---

## What's Happening

1. **Downloads installer** (~50KB)
2. **Checks your system** — WSL2, Docker Desktop, NVIDIA GPU
3. **Auto-fixes issues** — enables WSL2, prompts for Docker install
4. **Detects GPU** — picks right model tier automatically
5. **Downloads model** — 7B to 72B based on your VRAM (~10-40GB)
6. **Starts services** — vLLM, Open WebUI, search, database

**Total time:** 10-30 minutes depending on download speed.

---

## Quick Commands

```powershell
# Start after install
cd $env:LOCALAPPDATA\DreamServer
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# Check status
docker compose ps

# Update
docker compose pull && docker compose up -d
```

---

## Open the UI

Visit **http://localhost:3000**

First user becomes admin. Start chatting immediately.

---

## Bootstrap Mode (Faster Start)

Start with a tiny 1.5B model, upgrade later:

```powershell
.\install.ps1 -Bootstrap
```

Chat in 2 minutes while full model downloads in background.

---

## Common Flags

| Flag | What It Does |
|------|--------------|
| `-Bootstrap` | Quick start with small model |
| `-Tier 2` | Force specific tier (1-4) |
| `-Voice` | Enable Whisper + TTS |
| `-Workflows` | Enable n8n automation |
| `-Rag` | Enable Qdrant vector DB |
| `-All` | Everything enabled |
| `-Diagnose` | Check system only |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Docker not running" | Start Docker Desktop, wait for whale icon |
| "WSL2 not found" | `wsl --install` then restart |
| "nvidia-smi fails" | Update NVIDIA drivers; restart Docker Desktop |
| "Port in use" | Edit `.env`, change `WEBUI_PORT=3001` |
| Out of memory | Lower tier: `.\install.ps1 -Tier 1` |

Full guide: [WINDOWS-INSTALL-WALKTHROUGH.md](WINDOWS-INSTALL-WALKTHROUGH.md)

---

## System Requirements by Tier

| Tier | VRAM | Model | Use Case |
|------|------|-------|----------|
| 1 | 8-12GB | 7B Qwen | Basic chat, coding help |
| 2 | 12-20GB | 14B AWQ | Daily driver, good reasoning |
| 3 | 20-40GB | 32B AWQ | Power user, complex tasks |
| 4 | 40GB+ | 72B AWQ | Maximum capability |

---

## Architecture

```
Windows Host
  ├── Docker Desktop (WSL2 backend)
  │     ├── vLLM container (GPU accelerated)
  │     ├── Open WebUI (port 3000)
  │     ├── SearXNG search
  │     └── PostgreSQL + Qdrant
  └── WSL2 Ubuntu (file system, networking)
```

GPU access: Windows driver → WSL2 → Docker Container Toolkit → vLLM

---

## Files & Locations

| What | Where |
|------|-------|
| Install directory | `%LOCALAPPDATA%\DreamServer` |
| Config | `.env` file in install directory |
| Models | Docker volume `dream-server_model-cache` |
| Logs | `docker compose logs` |
| Data | Docker volumes (auto-managed) |

---

## Updating

```powershell
cd $env:LOCALAPPDATA\DreamServer
# Get latest
git pull
# Update containers
docker compose pull
# Restart
docker compose up -d
```

---

## Need Help?

- Full walkthrough: [WINDOWS-INSTALL-WALKTHROUGH.md](WINDOWS-INSTALL-WALKTHROUGH.md)
- GPU issues: [WSL2-GPU-TROUBLESHOOTING.md](WSL2-GPU-TROUBLESHOOTING.md)
- Docker tuning: [DOCKER-DESKTOP-OPTIMIZATION.md](DOCKER-DESKTOP-OPTIMIZATION.md)
- General FAQ: [FAQ.md](../FAQ.md)

---

*Last updated: 2026-02-13*
