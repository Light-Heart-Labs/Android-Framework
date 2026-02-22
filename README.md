# Lighthouse AI

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/Light-Heart-Labs/Lighthouse-AI)](https://github.com/Light-Heart-Labs/Lighthouse-AI)

**Your hardware. Your data. Your rules.**

One installer. Bare metal to fully running local AI stack in 10 minutes — LLM inference, chat UI, voice agents, workflow automation, RAG, and privacy tools. No subscriptions. No cloud. Runs entirely offline.

```bash
curl -fsSL https://raw.githubusercontent.com/Light-Heart-Labs/Lighthouse-AI/main/dream-server/get-dream-server.sh | bash
```

<!-- Screenshot/GIF: Add a recording of Dream Server running (dashboard + chat UI) here before launch -->

## What You Get

| | |
|---|---|
| **LLM Inference** (vLLM) | GPU-accelerated, auto-selects 7B to 72B models for your hardware |
| **Chat UI** (Open WebUI) | Full-featured chat interface with model management |
| **Voice** (Whisper + Kokoro + LiveKit) | Speech-to-text, text-to-speech, real-time WebRTC conversations |
| **Workflows** (n8n) | Visual workflow editor with 400+ integrations |
| **RAG** (Qdrant) | Vector database for document Q&A |
| **Privacy Shield** | PII redaction before anything leaves your network |
| **Dashboard** | Real-time GPU metrics, service health, system status |
| **API Gateway** (LiteLLM) | Multi-model routing, OpenAI-compatible API |
| **OpenClaw Agents** | Multi-agent AI coordination on local hardware |

### vs. The Alternatives

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

## Hardware Tiers (Auto-Detected)

The installer detects your GPU and picks the optimal model automatically:

| Tier | VRAM | Model | Example GPUs |
|------|------|-------|--------------|
| Entry | <12GB | Qwen2.5-7B | RTX 3080, RTX 4070 |
| Prosumer | 12-20GB | Qwen2.5-14B-AWQ | RTX 3090, RTX 4080 |
| Pro | 20-40GB | Qwen2.5-32B-AWQ | RTX 4090, A6000 |
| Enterprise | 40GB+ | Qwen2.5-72B-AWQ | A100, H100, multi-GPU |

Override: `./install.sh --tier 3` | Windows: [`install.ps1`](dream-server/README.md#windows) handles WSL2 + Docker automatically

**Bootstrap mode:** Starts a tiny model instantly, lets you chat in 2 minutes while the full model downloads in the background. Hot-swap with zero downtime when ready.

---

## OpenClaw — Multi-Agent AI on Your GPU

Dream Server ships with local [OpenClaw](https://openclaw.io) support out of the box — the multi-agent framework for AI agents coordinating autonomously on your hardware. Includes vLLM Tool Call Proxy, battle-tested configs, and workspace templates for agent identity.

This repo was born from the [OpenClaw Collective](COLLECTIVE.md) — 3 AI agents, 3,464 commits, 8 days, three shipping products built autonomously on local GPUs. Dream Server packages that into something anyone can set up in 10 minutes.

---

## Operations Toolkit

Standalone tools for running persistent AI agents in production. Each works independently — grab what you need.

| Tool | Purpose |
|------|---------|
| [**Guardian**](guardian/) | Self-healing process watchdog — monitors services, restores from backup, runs as root so agents can't kill it |
| [**Memory Shepherd**](memory-shepherd/) | Periodic memory reset to prevent identity drift in long-running agents |
| [**Token Spy**](token-spy/) | API cost monitoring with real-time dashboard and auto-kill for runaway sessions |
| [**vLLM Tool Proxy**](scripts/vllm-tool-proxy.py) | Makes local model tool calling work with OpenClaw — SSE re-wrapping, extraction, loop protection |
| [**LLM Cold Storage**](scripts/llm-cold-storage.sh) | Archives idle HuggingFace models to free disk, models stay resolvable via symlink |

[Toolkit install guide →](docs/SETUP.md) | [Philosophy & patterns →](docs/PHILOSOPHY.md)

---

## Documentation

| | |
|---|---|
| [**Dream Server QUICKSTART**](dream-server/QUICKSTART.md) | Step-by-step install guide |
| [**FAQ**](dream-server/FAQ.md) | Troubleshooting, usage, advanced config |
| [**Hardware Guide**](dream-server/docs/HARDWARE-GUIDE.md) | What to buy — GPU recommendations with real prices |
| [**Cookbook**](docs/cookbook/) | Recipes: voice agents, RAG, code assistant, privacy proxy, multi-GPU, swarms |
| [**Architecture**](docs/ARCHITECTURE.md) | How it all works under the hood |
| [**COLLECTIVE.md**](COLLECTIVE.md) | Origin story — the AI agents that built these tools |

---

## License

Apache 2.0 — see [LICENSE](LICENSE). Use it, modify it, ship it.

Built by [Lightheart Labs](https://github.com/Light-Heart-Labs) and the [Android Collective](COLLECTIVE.md).
