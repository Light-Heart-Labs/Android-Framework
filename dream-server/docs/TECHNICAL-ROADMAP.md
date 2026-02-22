# Dream Server: Technical Roadmap to a World-Class Product

**From "Developer Tool That Works" to "Premium Local AI Experience That Users Rave About"**

*Prepared for Light Heart Labs Engineering Team — February 2026*

---

## The Vision (In Michael's Words)

> "This isn't a developer tool, it's a premium local AI experience. Think Apple-level polish on open-source infrastructure. It should feel like a high-end curated ecosystem assembled just for you instantly and with ease. More approachable, polished, and capable than LM Studio. It comes with workflows already created, OpenClaw agents, an intelligent fully local voice assistant. Should feel like a dream."

This roadmap is built against that bar. Not "does it work?" but "does it make someone say *holy shit, this is running on MY hardware?*"

---

## Where We Are Today (Honest Assessment)

### What's Strong
- 880-line installer with hardware auto-detection — genuinely production quality
- Docker Compose orchestration with 11 services, 6 profiles — architecturally sound
- dream-cli with 11 commands — good operational tooling
- Documentation (HARDWARE-GUIDE, SECURITY, TROUBLESHOOTING) — best-in-class for the space
- Pricing/sales materials — surprisingly complete (ROI calculators, objection handling, case study templates)
- Stranger test guide exists — shows product thinking

### What's Broken
- Windows installer stops at line 100
- Bootstrap scripts (model-bootstrap.sh, upgrade-model.sh) don't exist
- Model download has zero retry logic
- All Docker images use latest tags
- QUICKSTART commands reference setup.sh subcommands that don't exist
- Dockerfile for voice agent references Flask app that doesn't exist

### What's Missing (The Real Gap)

The entire user-facing experience layer. Users get a powerful AI stack and then... a terminal. No dashboard. No model management. No onboarding. No feature discovery. No monitoring. No way to know what's running, what's broken, or what they're missing.

**The infrastructure is a 8/10. The experience is a 3/10.** That's the gap this roadmap closes.

---

## What "Incredible" Looks Like (Lessons From the Market)

From deep research into what users love and hate about Ollama, LM Studio, LocalAI, and Jan.ai:

### Users Rave About:
- **Ollama's 60-second install-to-inference** — Two commands, chatting with AI. The install command IS the marketing.
- **LM Studio's model browser** — Shows VRAM requirement vs your hardware BEFORE download. Green/yellow/red compatibility. Eliminates the #1 beginner mistake.
- **LM Studio's real-time telemetry** — Tokens/sec, time to first token, context usage visible while chatting. Educational AND confidence-building.
- **Jan's consumer-grade UI** — Looks like a product you'd show to your boss, not a weekend project.
- **Cursor's zero-switching-cost** — Imports your existing setup, works immediately, new capabilities layered on top.

### Users Hate:
- **Ollama's opaque GPU management** — "I know my hardware better than Ollama does"
- **LM Studio being closed source** — Privacy-conscious users running local AI can't verify what the tool does with their data
- **LocalAI's configuration nightmare** — YAML files, unhelpful errors, documentation that lags the codebase. The #1 reason people abandon it.
- **Jan's Electron overhead** — 400-600MB RAM for the UI on a machine where every MB matters for inference
- **Every tool's model storage mess** — No disk usage visibility, no deduplication, can't move to a different drive

### The Unbuilt Features Everyone Wants:
- Intelligent model routing (small model for simple questions, big for complex)
- Local/cloud hybrid with transparent failover
- "Train on my data" without ML knowledge (great RAG is the 80% solution)
- Resource-aware multi-service scheduling on one GPU
- Persistent memory across conversations
- **One-click full-stack AI deployment** — This IS Dream Server's pitch

### The Viral Pattern (Docker, Homebrew, VS Code, Cursor):
- **One-liner test** — Can adoption fit in a tweet?
- **Hallway test** — Can you demo it to a colleague in 2 minutes?
- **Removal test** — Can you cleanly uninstall? (Lowers psychological barrier to try)
- **Complaint graph** — Maps to an existing high-volume complaint
- **First-party integration** — Best experience with zero config beats better experience with config

**Dream Server's complaint graph match:** "I want a full local AI stack but setup takes a weekend." This is the most common meta-request on r/selfhosted for AI. Nobody has solved it well yet.

---

## The Roadmap: 6 Phases

### Guiding Principles

Every milestone is evaluated against three questions:
1. **Does it make the first 5 minutes feel like magic?**
2. **Does it make users discover capabilities they didn't know they had?**
3. **Does it make users feel confident their system is healthy and powerful?**

If a feature doesn't contribute to at least one of these, it's cut.

---

## Phase 0: Foundation Fixes (Week 1-2)

*"Make it actually work for a stranger"*

**Goal:** A stranger with an NVIDIA GPU and Linux/WSL can go from zero to chatting in under 10 minutes with zero errors.

### M0.1: Fix Critical Blockers

| Task | Detail | Effort | Owner |
|------|--------|--------|-------|
| Fix QUICKSTART/README inconsistency | Replace all setup.sh references with install.sh. One path, everywhere. | 30 min | Any |
| Write model-bootstrap.sh | Background download of full model while 1.5B serves requests. Progress file at ~/.dream-server/model-download.status. 3 retries with exponential backoff. | 4 hrs | Backend |
| Write upgrade-model.sh | Graceful vLLM stop → model directory swap → vLLM restart → health check → report success/failure. Atomic: if new model fails, rollback to previous. | 3 hrs | Backend |
| Add retry logic to model download in install.sh | 3 attempts, exponential backoff (2s, 8s, 32s), timeout at 2 hours, progress logging to user-visible file. | 2 hrs | Backend |
| Pin all Docker image versions | Research current stable tags for all 11 services. Pin to version@sha256:digest. Create COMPATIBILITY-MATRIX.md. | 3 hrs | DevOps |
| Fix voice agent Dockerfile | Currently references shield:app — no Flask app exists. Fix to match actual agent.py entry point. | 1 hr | Backend |
| Add dream test command | Sends test prompt to vLLM, checks response, verifies all enabled services respond. Outputs "Dream Server is ready!" or specific failure. | 2 hrs | Backend |

### M0.2: Complete Windows Path

| Task | Detail | Effort |
|------|--------|--------|
| Complete install.ps1 | Full parity with install.sh: WSL2 detection/install, Docker Desktop detection, GPU passthrough verification, .env generation, health checks. | 12 hrs |
| Test on fresh Windows 11 VM | Clean install, NVIDIA driver only. Run install.ps1 end-to-end. Document every friction point. | 4 hrs |
| WSL2 GPU passthrough troubleshooting guide | Step-by-step for the 5 most common failure modes. Screenshots. | 3 hrs |

### M0.3: Separate Repository

| Task | Detail | Effort |
|------|--------|--------|
| Extract dream-server/ to its own repo | github.com/Lightheartdevs/dream-server. Clean history. Proper LICENSE, CONTRIBUTING, issue templates. | 3 hrs |
| Create curl one-liner installer | `curl -fsSL https://raw.githubusercontent.com/Light-Heart-Labs/Lighthouse-AI/main/dream-server/install.sh \| bash` — downloads repo, runs installer. Like Homebrew's install. | 2 hrs |
| Set up GitHub Actions CI | Lint bash scripts (shellcheck), validate docker-compose syntax, run integration-test.sh on every PR. | 3 hrs |

**Exit Criteria:** Fresh Windows 11 and Ubuntu 22.04 machines can both go from zero to chatting in under 10 minutes. `dream test` passes. One-liner install works.

---

## Phase 1: The Magic First 5 Minutes (Week 3-5)

*"Install it once, tell everyone you know"*

**Goal:** The experience from `curl ... | bash` to "I'm talking to a local AI" feels choreographed, fast, and delightful. Users understand what they have and want to explore more.

### M1.1: Installer Experience Overhaul

**Current:** Terminal output with colored text.
**Target:** A cinematic install that builds excitement.

```
 ╔══════════════════════════════════════════════════════════════╗
 ║                                                              ║
 ║   ☽  D R E A M   S E R V E R                                ║
 ║                                                              ║
 ║   Your personal AI. Running on your hardware.                ║
 ║   Private. Powerful. Yours.                                  ║
 ║                                                              ║
 ╚══════════════════════════════════════════════════════════════╝

 Scanning your hardware...

   GPU:    NVIDIA RTX 4070 Ti Super — 16GB VRAM
   CPU:    AMD Ryzen 7 7800X3D — 8 cores
   RAM:    64GB DDR5
   Disk:   412GB available

 Recommendation: Prosumer Tier
   Model:  Qwen2.5-32B-Instruct (quantized, fits your 16GB)
   Speed:  ~55 tokens/second
   Users:  5-8 concurrent comfortably

 What would you like?

   [1] Full Stack (recommended)
       Chat + Voice + Workflows + Document Q&A
       Uses ~14GB VRAM, all features enabled

   [2] Core Only
       Chat interface + API
       Uses ~12GB VRAM, minimal footprint

   [3] Custom
       Choose exactly what you want

 →
```

| Task | Detail | Effort |
|------|--------|--------|
| Redesign installer output | Branded header, clean hardware summary, recommendation with reasoning, numbered feature selection. Progress bars for each phase (not just dots). | 6 hrs |
| Add download progress bars | Use curl --progress-bar or wget with progress for Docker image pulls and model downloads. Show actual MB transferred, speed, ETA. | 4 hrs |
| Add time estimates per phase | "Pulling containers... (~3 minutes)" based on detected internet speed (quick test download). | 2 hrs |
| Smart defaults based on hardware | If 24GB+ VRAM, default to Full Stack. If 8-12GB, default to Core Only. Explain why. | 2 hrs |
| Post-install summary card | Show exactly what was installed, all URLs with ports, credentials (masked), and a QR code for the WebUI URL (for phone access on LAN). | 3 hrs |

### M1.2: Welcome Dashboard (The "Wow" Moment)

**This is the single highest-impact feature in the entire roadmap.**

When the user opens http://localhost:3000 for the first time, they should NOT see a blank Open WebUI login. They should see Dream Server's own welcome experience.

**Architecture:** A lightweight web app (Vite + React or even plain HTML/JS) served at localhost:3001 (Dream Server Dashboard). Open WebUI stays at localhost:3000 as the chat interface.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ☽ Dream Server                            v1.0 | Prosumer      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Welcome to your AI.                                            │
│                                                                  │
│  Everything is running on this machine. Your data never         │
│  leaves your network. No subscriptions. No limits.              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  💬 Chat     │  │  🎤 Voice    │  │  📄 Documents│          │
│  │              │  │              │  │              │          │
│  │  Talk to     │  │  Speak to    │  │  Upload &    │          │
│  │  your AI     │  │  your AI     │  │  ask about   │          │
│  │              │  │              │  │  your files  │          │
│  │  [Open →]    │  │  [Try it →]  │  │  [Start →]   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  ⚡ Workflows│  │  🤖 Agents   │  │  📊 System   │          │
│  │              │  │              │  │              │          │
│  │  Automate    │  │  OpenClaw    │  │  GPU, health │          │
│  │  anything    │  │  multi-agent │  │  & services  │          │
│  │              │  │              │  │              │          │
│  │  [Explore →] │  │  [Launch →]  │  │  [Status →]  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ── Your System ──────────────────────────────────────────────  │
│                                                                  │
│  GPU: RTX 4070 Ti Super    VRAM: ████████░░ 13.2/16 GB         │
│  Model: Qwen2.5-32B-AWQ    Speed: 54 tok/s                     │
│  Services: 6/6 healthy     Uptime: 2h 14m                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Task | Detail | Effort |
|------|--------|--------|
| Build Dream Dashboard web app | Vite + React (or Svelte for smaller bundle). Single-page app. Talks to Docker API + nvidia-smi via a tiny backend API. | 2 weeks |
| System status API | Lightweight Python/Node service that exposes: container status, GPU metrics (nvidia-smi JSON), service health checks, model info, disk usage. Polled every 5s. | 3 days |
| Service cards with status indicators | Green/yellow/red per service. Show port, uptime, last restart. Click to open service (WebUI, n8n, etc). | 3 days |
| GPU/system metrics display | Real-time VRAM usage bar, GPU utilization %, temperature, CPU, RAM. Updates every 5s. | 2 days |
| First-run welcome flow | If no chat history detected, show welcome message explaining what they have. Feature cards link to each capability. Dismiss permanently after first visit. | 2 days |
| Add to docker-compose.yml | New dream-dashboard service. Port 3001. Depends on all other services. Auto-starts. | 2 hrs |

### M1.3: Bootstrap Mode That Actually Feels Good

**Current:** User waits 10-30 minutes staring at terminal.
**Target:** User is chatting in 90 seconds with a small model while the full model downloads in the background with visible progress.

```
┌─────────────────────────────────────────────────────────────────┐
│  ☽ Dream Server                                    Bootstrap    │
│                                                                  │
│  You're chatting with a lightweight model while your            │
│  full-power model downloads in the background.                  │
│                                                                  │
│  Full model: Qwen2.5-32B-AWQ                                    │
│  Download:   ████████████░░░░░░░░  62% (9.8 / 15.7 GB)         │
│  ETA:        ~8 minutes                                         │
│                                                                  │
│  When ready, your AI will automatically upgrade.                │
│  No restart needed. Your conversation continues.                │
│                                                                  │
│  [Dismiss]                                                      │
└─────────────────────────────────────────────────────────────────┘
```

| Task | Detail | Effort |
|------|--------|--------|
| Bootstrap progress file | model-bootstrap.sh writes JSON progress to /data/bootstrap-status.json — percent, bytes, speed, ETA. Dashboard reads this. | 2 hrs |
| Dashboard bootstrap banner | Shows download progress when bootstrap active. Auto-dismisses when complete. Celebratory animation on completion ("Your full-power AI is ready!"). | 4 hrs |
| Hot-swap without restart | Use vLLM's model loading API to swap models without container restart. If not possible, gracefully restart vLLM with user notification. | 6 hrs |
| Conversation continuity | Ensure chat history survives model swap. Open WebUI should not lose context. | 2 hrs |

**Exit Criteria:** User runs one-liner install → sees branded installer with progress bars → opens Dashboard showing all services green → clicks "Chat" → is talking to AI in under 2 minutes → sees bootstrap progress → gets notification when full model ready. On a fresh machine, total time to first chat: under 5 minutes.

---

## Phase 2: The Ecosystem Feel (Week 6-9)

*"Not a tool, an experience"*

**Goal:** Dream Server feels like a curated ecosystem where everything is connected and discoverable, not a collection of Docker containers.

### M2.1: Model Manager

The #2 most impactful feature after the Dashboard. Users need to be able to explore, download, switch, and manage models without touching a terminal.

| Task | Detail | Effort |
|------|--------|--------|
| Model catalog API | Curated list of recommended models per hardware tier. Metadata: name, size, VRAM requirement, speed estimate, specialty (code, creative, multilingual), license. Stored as JSON, fetched from GitHub or bundled. | 1 day |
| Model browser UI (Dashboard page) | Grid/list of models. Filter by: fits my GPU (green/yellow/red), size, specialty. Show VRAM bar comparing model requirement vs available. | 3 days |
| One-click download with progress | Click "Download" → progress bar with speed/ETA → "Ready to Load". Downloads run in background. Queue multiple downloads. | 3 days |
| Model switching | "Load" button swaps active model. Shows current model, confirm before switching. Restart vLLM with new model. Graceful with health check. | 2 days |
| Storage management | Show disk usage per model. "Delete" button with confirmation. "You have 3 models using 42GB. Free up space?" | 1 day |
| dream model CLI commands | `dream model list`, `dream model download <name>`, `dream model switch <name>`, `dream model delete <name>`. Mirror everything in the UI. | 2 days |

### M2.2: Workflow Gallery (Not Just n8n)

n8n is powerful but intimidating. Dream Server should present workflows as "capabilities you can enable," not "automation tools to learn."

| Task | Detail | Effort |
|------|--------|--------|
| Workflow gallery page (Dashboard) | Cards for each pre-built workflow. Name, description, what it does in plain English, what services it needs, one-click import. | 3 days |
| Visual workflow explanation | For each workflow, a simple diagram: "You upload a document → AI reads it → You ask questions → AI answers using the document." No n8n node graphs. | 2 days |
| One-click import + validation | "Enable" button checks all required services are running, imports workflow into n8n, activates it, confirms it's live. If a dependency is missing, offers to enable it. | 3 days |
| 5 additional workflow templates | Slack bot, Discord bot, email auto-responder, daily digest summary, meeting notes transcriber. Each with plain-English description and one-click import. | 5 days |
| Workflow status in Dashboard | Shows active workflows, execution count, last run, success/failure rate. "Your Document Q&A workflow has answered 47 questions this week." | 2 days |

### M2.3: Voice Agent That Feels Like Talking to Jarvis

**Current:** Whisper and Piper as separate services, no unified voice experience.
**Target:** Click a button, talk to your AI, hear it respond. Like talking to a smart assistant that runs on YOUR machine.

| Task | Detail | Effort |
|------|--------|--------|
| Voice interface page (Dashboard) | Full-page voice mode. Large microphone button. Real-time transcription as you speak. AI response plays back as audio. Conversation history visible. | 1 week |
| WebRTC audio pipeline | Browser microphone → WebRTC → Whisper STT → vLLM → Kokoro TTS → audio playback. Target: under 3 seconds end-to-end on Tier 2+. | 1 week |
| Voice Activity Detection (VAD) | Silero VAD to detect when user stops speaking. No need to hold a button — speak naturally, AI responds when you pause. Push-to-talk as fallback. | 3 days |
| Real-time transcription display | Show words as they're recognized. User sees their speech appearing in text. Confidence indicator. | 2 days |
| Interrupt handling | If user starts speaking while AI is responding, stop the audio playback and listen. Natural conversation flow. | 2 days |
| Voice settings | Voice selection (Piper voices), speech speed, auto-play toggle, wake word (optional, "Hey Dream"). Persistent per user. | 2 days |
| Complete voice agent code | Finish agents/voice/agent.py. Full LiveKit integration. Error handling for audio glitches. Graceful fallback if Whisper/Piper unavailable. | 3 days |

### M2.4: Feature Discovery Engine

Users should organically discover capabilities they didn't know they had.

| Task | Detail | Effort |
|------|--------|--------|
| Hardware-aware suggestions | Dashboard shows: "Your GPU has capacity for Voice (currently disabled). Enable in 1 click?" Based on VRAM headroom calculation. | 2 days |
| Contextual prompts in chat | System prompt includes capability awareness. If user says "can you listen to audio?" → "Yes! Voice mode is available. [Enable Voice]" | 1 day |
| Capability maturity display | Dashboard footer: "You're using 3 of 6 available features. [Explore more →]" Progress bar fills as features are enabled. | 1 day |
| Feature cards with effort estimates | "Document Q&A — Upload files and ask questions. Setup time: ~2 minutes. Needs: 1GB additional disk." | 1 day |
| "What can my AI do?" system prompt | When user asks variations of "what can you do?", response includes all enabled features with examples. | 2 hrs |

**Exit Criteria:** Users can browse/download/switch models from the Dashboard. Voice works end-to-end with under 3s latency. Workflows are discoverable and importable with one click. Users naturally discover features they haven't enabled yet.

---

## Phase 3: Confidence & Reliability (Week 10-13)

*"I trust this system to run 24/7"*

**Goal:** Users feel confident their system is healthy, know when something's wrong, and problems fix themselves when possible.

### M3.1: Monitoring & Observability Dashboard

| Task | Detail | Effort |
|------|--------|--------|
| Time-series metrics collection | Poll Docker stats + nvidia-smi every 10s. Store in SQLite (lightweight, no external dependency). 30-day retention with hourly rollups. | 3 days |
| GPU metrics graphs | VRAM usage over time, GPU utilization, temperature. 1-hour, 24-hour, 7-day views. Zoom/pan. | 3 days |
| Inference metrics | Requests/minute, latency histogram (p50/p95/p99), tokens/second, error rate. Per-model breakdown. | 3 days |
| Service health timeline | When did each service start/stop/crash? Visual timeline. "vLLM restarted 3 times yesterday — investigate?" | 2 days |
| Alert system | Configurable thresholds. GPU > 95% for 10+ minutes → dashboard warning. Service crashed > 3x in 1 hour → red alert. Disk > 90% → cleanup suggestion. | 3 days |
| Alert channels | Dashboard notification bell + optional Discord webhook + optional email. | 2 days |

### M3.2: Self-Healing & Graceful Degradation

| Task | Detail | Effort |
|------|--------|--------|
| Service watchdog | If a service goes down, auto-restart (max 3x/hour). If still failing, mark as degraded, alert user, suggest troubleshooting. | 3 days |
| OOM recovery | If vLLM OOMs, auto-reduce MAX_CONTEXT by 50%, restart, notify user. "Running in reduced context mode to prevent crashes." | 2 days |
| Graceful feature degradation | If Whisper crashes, voice input disabled but chat still works. If Qdrant down, RAG disabled but chat works. Each feature fails independently. Dashboard shows which features are degraded. | 3 days |
| Request queuing | If vLLM is busy, queue requests instead of timing out. Show "Position in queue: 3" to user. Process in order. | 3 days |
| Startup health validation | After every restart, run `dream test` automatically. If any service fails, show specific diagnostic in Dashboard. Don't declare "ready" until all enabled services pass. | 2 days |

### M3.3: Update System

| Task | Detail | Effort |
|------|--------|--------|
| Version tracking | `dream version` shows installed version, install date, last update. Version stored in ~/.dream-server/version.json. | 1 day |
| Update checker | On Dashboard load, check GitHub releases API for newer version. Show banner: "Update available: v1.2 — includes voice latency improvements." Non-intrusive. | 2 days |
| Safe update flow | `dream update` → backup .env → pull new images → run migrations → health check → rollback if failed. Show changelog before proceeding. | 3 days |
| Rollback capability | Keep previous image digests. `dream rollback` restores last known good state. | 2 days |
| Uninstall script | `dream uninstall` — stops services, removes containers, optionally removes data. Clean. Users feel safe trying because they can undo. | 2 hrs |

### M3.4: Comprehensive Testing

| Task | Detail | Effort |
|------|--------|--------|
| End-to-end test suite | Script that: installs fresh, waits for services, sends chat request, tests voice (if enabled), tests RAG (if enabled), validates all health endpoints. Run in CI on every PR. | 1 week |
| Load testing | Simulate 5, 10, 20 concurrent users. Measure latency degradation. Document per-tier capacity. Publish in HARDWARE-GUIDE. | 3 days |
| Chaos testing | Kill random services during operation. Verify watchdog restarts them. Verify Dashboard shows correct status. Verify no data loss. | 3 days |
| Cross-platform test matrix | Ubuntu 22.04, Ubuntu 24.04, Windows 11 + WSL2, with RTX 3060/4070/4090. Automated where possible, manual where not. | 1 week |
| User acceptance testing | 5-10 beta testers (mix of technical and non-technical). Follow Stranger Test Guide. Collect feedback using the feedback template. Fix top 5 friction points. | 2 weeks |

**Exit Criteria:** Dashboard shows 30 days of metrics. Alerts fire when things break. Self-healing handles common failures. Updates are safe and reversible. Test suite catches regressions.

---

## Phase 4: Delight & Differentiation (Week 14-18)

*"Nothing else is like this"*

**Goal:** Features that make Dream Server genuinely unique — things no competitor offers.

### M4.1: Intelligent Model Routing

The feature nobody has built yet. Small model for simple questions, big model for complex ones. Automatic.

| Task | Detail | Effort |
|------|--------|--------|
| Query complexity classifier | Lightweight classifier (regex + heuristics, not another LLM call): prompt length, question complexity markers, code detection, multi-step reasoning indicators. Routes to "fast" or "powerful" model. | 3 days |
| Multi-model support in vLLM | Load two models (e.g., 7B + 32B) if VRAM allows. LiteLLM proxy routes based on classifier output. | 3 days |
| Dashboard routing controls | Show routing decisions in real-time. "This question was routed to Qwen-7B (simple query)." Let users override: "Always use the big model for code questions." | 2 days |
| Routing analytics | "This week: 73% of your queries used the fast model, saving 4 hours of GPU time." | 1 day |

### M4.2: Persistent Memory

Users want their AI to remember them.

| Task | Detail | Effort |
|------|--------|--------|
| Memory extraction service | After each conversation, extract key facts: user preferences, project names, technical decisions, personal details. Store in a memory database (SQLite or Qdrant). | 1 week |
| Memory injection | At conversation start, inject relevant memories into system prompt. "You previously told me you prefer Python over JavaScript and you're working on a healthcare app." | 3 days |
| Memory management UI | Dashboard page: "Your AI Remembers." List of extracted facts. Edit, delete, or add memories manually. Privacy control: "Forget everything about project X." | 3 days |
| Memory + RAG integration | Memories and uploaded documents searchable together. "What did I say about the API design last week?" searches both conversation memory and documents. | 2 days |

### M4.3: Resource-Aware Scheduling

One GPU, multiple services, zero fighting.

| Task | Detail | Effort |
|------|--------|--------|
| VRAM budget manager | Track VRAM allocation per service. Priority system: Chat (highest) > Voice (high) > RAG indexing (medium) > Background tasks (low). | 3 days |
| Dynamic model loading/unloading | If voice hasn't been used in 30 minutes, unload Whisper model, free VRAM for larger context. Reload on demand (with latency notification). | 3 days |
| Service scheduling display | Dashboard shows: "Active: Chat (13GB), Voice (2GB). Idle: RAG indexing paused, will resume when GPU is free." | 2 days |
| User priority policies | "Prioritize voice latency over chat throughput" — configurable in Dashboard settings. | 1 day |

### M4.4: Configuration Sharing & Templates

| Task | Detail | Effort |
|------|--------|--------|
| dream config export/import | Export full config to YAML (secrets redacted). Import validates hardware compatibility before applying. | 2 days |
| Configuration templates | "Optimized for coding," "Optimized for voice," "Optimized for documents," "Balanced." One-click apply from Dashboard. | 2 days |
| Team sharing | Export redacted configs. Teammate imports, enters their own secrets. Same stack, different credentials. | 1 day |
| Config diff display | "You're about to change 4 settings. VRAM usage will increase by 3GB. GPU might be tight." Confirm before applying. | 1 day |

### M4.5: Plugin System (Foundation)

| Task | Detail | Effort |
|------|--------|--------|
| Plugin interface spec | Define interfaces for STT, TTS, embedding, and LLM backend plugins. YAML config to swap implementations. | 2 days |
| Faster-Whisper plugin | Drop-in replacement for Whisper with 3-5x speed improvement. Same API, different backend. First proof of plugin system. | 3 days |
| Plugin management in Dashboard | Show installed plugins, available plugins, one-click install/swap. "Replace Whisper with Faster-Whisper for 3x speed?" | 3 days |
| Plugin developer documentation | How to build a Dream Server plugin. Template repo. Testing guide. | 2 days |

**Exit Criteria:** Model routing works automatically and visibly. AI remembers users across sessions. GPU resources managed intelligently. Configs shareable. Plugin system has at least 2 working plugins.

---

## Phase 5: Polish & Scale (Week 19-24)

*"Ready for Product Hunt"*

**Goal:** The product is polished enough to launch publicly and handle the attention.

### M5.1: Landing Page & Distribution

| Task | Detail | Effort |
|------|--------|--------|
| dreamserver.dev landing page | Hero: "Your AI. Your Hardware. Your Rules." One-liner install command prominently displayed. Feature showcase with screenshots. Hardware tier recommendations. ROI calculator (you already have the spec). | 1 week |
| Demo video | 90-second screencast: install → dashboard → chat → voice → workflow. No narration needed, just smooth editing with captions. | 2 days |
| SEO content | "How to run ChatGPT locally," "Local AI setup guide 2026," "Best self-hosted AI stack." Blog posts linking to Dream Server. | 3 days |
| Analytics | Privacy-respecting analytics on landing page (Plausible, not Google Analytics). Track: visits, install command copies, GitHub stars. | 1 day |

### M5.2: Community Infrastructure

| Task | Detail | Effort |
|------|--------|--------|
| Discord server | Channels: #general, #support, #showcase, #feature-requests, #development. Moderation bot. Welcome message with getting-started links. | 4 hrs |
| GitHub Discussions | Enable on repo. Categories: Q&A, Ideas, Show & Tell, Announcements. Pin FAQ post. | 2 hrs |
| Issue templates | Bug report (with hardware/OS/version fields), feature request, documentation improvement. | 1 hr |
| CONTRIBUTING.md | How to contribute: code style, PR process, how to run tests, architecture overview. Make it inviting. | 3 hrs |
| Community showcase | Dashboard "Share" button generates a shareable card (image) of your setup: hardware, model, features enabled, uptime. Post to Discord #showcase. | 2 days |

### M5.3: Mobile-Responsive Dashboard

| Task | Detail | Effort |
|------|--------|--------|
| Responsive Dashboard design | All Dashboard pages work on phone/tablet (for LAN access). Service status cards stack vertically. GPU metrics readable on small screens. | 3 days |
| QR code for LAN access | Installer shows QR code for http://<local-ip>:3001. Scan with phone, open Dashboard. | 2 hrs |
| Mobile voice interface | Voice mode works on phone browser. Tap to talk, hear response. Like having Siri but local. | 2 days |

### M5.4: Performance Optimization

| Task | Detail | Effort |
|------|--------|--------|
| Dashboard performance | Lazy-load metric graphs. SSE instead of polling for real-time updates. Target: Dashboard loads in <1s. | 2 days |
| vLLM optimization profiles | Per-tier vLLM launch flags optimized for throughput vs latency. --max-num-seqs, --gpu-memory-utilization, --enforce-eager. Document the tradeoffs. | 2 days |
| Startup time optimization | Parallel service startup where possible. Target: all services healthy in under 60s (after model is cached). | 2 days |
| Cold start optimization | First-token latency optimization. Pre-warm model with dummy request on startup. Target: <500ms first-token for cached model. | 1 day |

### M5.5: Security Hardening for Production

| Task | Detail | Effort |
|------|--------|--------|
| Docker image vulnerability scan | Integrate `docker scout` into CI. Block releases with critical CVEs. | 1 day |
| Python dependency audit | `safety check` on all requirements.txt files. Pin transitive dependencies. | 1 day |
| Rate limiting | Optional per-user rate limiting in Dashboard. Prevent one user from monopolizing GPU. | 2 days |
| Audit logging | Who accessed what, when. Stored locally. Viewable in Dashboard. Required for enterprise compliance. | 2 days |
| HTTPS guide with auto-cert | Caddy reverse proxy config that auto-provisions Let's Encrypt certs. One-click enable from Dashboard for LAN-exposed setups. | 2 days |

**Exit Criteria:** Landing page live. Install command works from the internet. Discord active. Dashboard works on mobile. Product Hunt-ready.

---

## Phase 6: Enterprise & Revenue (Week 25+)

*"The business model kicks in"*

### M6.1: Licensing & Activation

| Task | Detail | Effort |
|------|--------|--------|
| License tier system | Free (community), Pro ($X/month or $Y/year), Enterprise (custom). Free = full features, no auto-updates. Pro = auto-updates, priority support. Enterprise = SLA, custom integrations. | 1 week |
| License key system | Generate/validate license keys. Dashboard shows tier. Graceful degradation for expired licenses (features keep working, updates stop). | 3 days |
| Private update server | Pro/Enterprise users get updates from private CDN, not public GitHub. Faster, more reliable, version-controlled. | 3 days |

### M6.2: Multi-User & Admin

| Task | Detail | Effort |
|------|--------|--------|
| User management | Admin can create/delete users, set quotas (tokens/month), assign roles (admin, user, viewer). | 1 week |
| Usage analytics | Per-user: tokens consumed, requests, models used, voice minutes. Exportable. | 3 days |
| Cost allocation | "Marketing team used 2M tokens this month, Engineering used 5M." For chargeback in larger organizations. | 2 days |

### M6.3: High Availability

| Task | Detail | Effort |
|------|--------|--------|
| Multi-node support | Kubernetes Helm chart for multi-GPU clusters. Load balancing across vLLM instances. | 2 weeks |
| Automated backups | Daily backup of configs, conversation history, memories, vector DB. Configurable retention. One-click restore. | 3 days |
| Disaster recovery guide | Step-by-step: backup → new hardware → restore → verify. | 1 day |

---

## Timeline Summary

| Phase | Weeks | Theme | Key Deliverable |
|-------|-------|-------|-----------------|
| Phase 0 | 1-2 | Fix foundations | Stranger can install without errors |
| Phase 1 | 3-5 | Magic first 5 minutes | Dashboard, bootstrap, branded install |
| Phase 2 | 6-9 | Ecosystem feel | Model manager, voice agent, workflow gallery |
| Phase 3 | 10-13 | Confidence & reliability | Monitoring, self-healing, updates, testing |
| Phase 4 | 14-18 | Delight & differentiation | Model routing, memory, resource scheduling, plugins |
| Phase 5 | 19-24 | Polish & scale | Landing page, community, mobile, security |
| Phase 6 | 25+ | Enterprise & revenue | Licensing, multi-user, HA |

---

## What Makes Users Rave (The Moments That Matter)

These are the specific moments in the user journey that generate word-of-mouth:

1. **"It detected my hardware and just... worked."** — The installer knows your GPU, picks the right model, and configures everything. No choices required. This is the Ollama moment.

2. **"I was chatting in 90 seconds."** — Bootstrap mode. Small model serves immediately while the real model downloads. Progress bar visible. Auto-upgrade. This is the Cursor moment (immediate value, no waiting).

3. **"The dashboard shows me everything."** — Open one page, see all services, GPU usage, model info, alerts. No terminal needed. This is the LM Studio telemetry moment, but for the whole stack.

4. **"I just clicked 'Download' and switched models."** — Model manager with hardware compatibility indicators. Green means it fits. Click, wait, done. This is the LM Studio model browser moment, but better (integrated with the rest of the stack).

5. **"I talked to it. With my voice. On my machine."** — Voice mode in the Dashboard. Click mic, speak, hear response. Under 3 seconds. This is the "holy shit" moment no competitor has.

6. **"It already had workflows set up."** — Document Q&A, voice transcription, daily digest — all pre-built. Click "Enable." This is the Apple ecosystem moment (everything works together).

7. **"It remembers me."** — Next session, AI knows your name, your projects, your preferences. Not because it sent your data to a cloud. Because it stored memories locally. This is the moment no local AI tool has achieved.

8. **"It fixed itself."** — Service crashed, watchdog restarted it, Dashboard showed a notification. User didn't have to do anything. This is the "it just works" moment.

---

## Effort Estimates Summary

| Phase | Engineering Weeks (1 developer) | Parallelizable? |
|-------|--------------------------------|-----------------|
| Phase 0 | 2-3 weeks | Mostly serial |
| Phase 1 | 3-4 weeks | Dashboard + installer in parallel |
| Phase 2 | 4-5 weeks | Model manager + voice + workflows in parallel |
| Phase 3 | 3-4 weeks | Monitoring + testing in parallel |
| Phase 4 | 4-5 weeks | All features parallelizable |
| Phase 5 | 3-4 weeks | Landing page + polish in parallel |
| Phase 6 | 4+ weeks | Depends on business decisions |
| **Total** | **~24-28 weeks** | With 2-3 developers: 12-16 weeks |

---

## The One Decision That Matters Most

**If you build nothing else from this roadmap, build the Dream Dashboard.**

It transforms the product from "powerful but invisible" to "powerful and I can see it." It's where users land, where they discover features, where they monitor health, where they manage models, where they feel confident. Every other feature in this roadmap is amplified by having a central place where users interact with the system.

**The Dashboard is the product. Everything else is infrastructure.**
