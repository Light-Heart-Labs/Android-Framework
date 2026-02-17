# Local AI Cookbook

Step-by-step practical recipes for self-hosted AI systems. Each recipe is standalone — pick the one that matches what you're building.

## Recipes

| # | Recipe | What You'll Build | GPU Required? |
|---|--------|------------------|---------------|
| 01 | [Voice Agent Setup](01-voice-agent-setup.md) | Whisper STT + vLLM + Kokoro TTS pipeline | Yes |
| 02 | [Document Q&A](02-document-qa-setup.md) | RAG system with Qdrant/ChromaDB + local LLM | Optional |
| 03 | [Code Assistant](03-code-assistant-setup.md) | Tool-calling code agent with file ops | Yes |
| 04 | [Privacy Proxy](04-privacy-proxy-setup.md) | PII-stripping proxy for cloud API calls | No |
| 05 | [Multi-GPU Cluster](05-multi-gpu-cluster.md) | Load-balanced multi-node GPU inference | Yes (2+) |
| 06 | [Swarm Patterns](06-swarm-patterns.md) | Sub-agent parallelization and coordination | Yes |
| 08 | [n8n + Local LLM](08-n8n-local-llm.md) | Workflow automation with local models | Yes |
| — | [Agent Template](agent-template-code.md) | Code specialist agent with debugging protocol | Yes |

## I Want To...

| Goal | Start With |
|------|-----------|
| Run a voice assistant locally | [Recipe 01](01-voice-agent-setup.md) |
| Search my documents with AI | [Recipe 02](02-document-qa-setup.md) |
| Build a local code copilot | [Recipe 03](03-code-assistant-setup.md) |
| Use cloud AI without leaking data | [Recipe 04](04-privacy-proxy-setup.md) |
| Scale across multiple GPUs | [Recipe 05](05-multi-gpu-cluster.md) |
| Run multiple agents in parallel | [Recipe 06](06-swarm-patterns.md) |
| Automate workflows with AI | [Recipe 08](08-n8n-local-llm.md) |
| Set up a coding agent from scratch | [Agent Template](agent-template-code.md) |

## Prerequisites

All recipes assume you have:
- A Linux machine (Ubuntu 22.04+ recommended)
- Python 3.10+
- Docker installed

GPU recipes additionally need:
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit
- vLLM installed (see [SETUP.md](../SETUP.md) for base installation)

## Related Docs

- [SETUP.md](../SETUP.md) — Base vLLM + OpenClaw installation
- [HARDWARE-GUIDE.md](../research/HARDWARE-GUIDE.md) — GPU buying guide with real benchmarks
- [ARCHITECTURE.md](../ARCHITECTURE.md) — How the tool call proxy works
- [PATTERNS.md](../PATTERNS.md) — Transferable patterns for persistent agents
