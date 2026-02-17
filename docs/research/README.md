# Research

Technical research and benchmarks from running persistent LLM agents on local hardware. These are real-world findings, not theoretical estimates.

## Documents

| Document | What It Covers |
|----------|---------------|
| [HARDWARE-GUIDE.md](HARDWARE-GUIDE.md) | GPU buying guide — tiers, prices, what NOT to buy, used market analysis |
| [GPU-TTS-BENCHMARK.md](GPU-TTS-BENCHMARK.md) | Text-to-speech latency benchmarks (GPU vs CPU, concurrency scaling) |
| [OSS-MODEL-LANDSCAPE-2026-02.md](OSS-MODEL-LANDSCAPE-2026-02.md) | Open-source model comparison — Qwen, Llama, tool-calling success rates |

## How These Relate to the Rest

- **Building a cluster?** Start with [HARDWARE-GUIDE.md](HARDWARE-GUIDE.md), then follow [cookbook/05-multi-gpu-cluster.md](../cookbook/05-multi-gpu-cluster.md)
- **Setting up voice agents?** Check [GPU-TTS-BENCHMARK.md](GPU-TTS-BENCHMARK.md) for latency expectations, then [cookbook/01-voice-agent-setup.md](../cookbook/01-voice-agent-setup.md)
- **Choosing a model?** Read [OSS-MODEL-LANDSCAPE-2026-02.md](OSS-MODEL-LANDSCAPE-2026-02.md), then see [SETUP.md](../SETUP.md) for deployment
