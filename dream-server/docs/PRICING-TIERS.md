# Dream Server Pricing & Tier Guide

*Client-ready reference for Light Heart Labs sales conversations*

---

## Executive Summary

Dream Server is a turnkey local AI package that runs enterprise-grade AI on client-owned hardware. This guide outlines hardware tiers, capabilities, costs, and ROI vs. cloud API alternatives.

**The pitch:** One-time hardware investment replaces perpetual cloud API fees, with typical ROI in 3-6 months for active teams.

---

## Hardware Tiers at a Glance

| Tier | Investment | Primary GPU | Target User | Concurrent Users |
|------|-----------|-------------|-------------|------------------|
| **Entry** | $800-1,200 | RTX 3060 12GB | Solo practitioner | 1-3 |
| **Prosumer** | $2,000-3,000 | RTX 4070 Ti Super 16GB | Small team | 5-8 |
| **Pro** | $4,000-6,000 | RTX 4090 24GB | Growing business | 10-20 |
| **Enterprise** | $12,000-18,000 | 2x RTX 4090 | Organization | 20-40+ |

---

## Tier 1: Entry ($800-1,200)

### What's Included
| Component | Specification | Estimated Cost |
|-----------|--------------|----------------|
| GPU | RTX 3060 12GB (new or used) | $200-350 |
| CPU | Intel i5-12400 / Ryzen 5 5600 | $150-200 |
| RAM | 32GB DDR4 | $80-100 |
| Storage | 500GB NVMe SSD | $50-70 |
| PSU | 550W 80+ Bronze | $60-80 |
| Case + Misc | Mid-tower, fans | $100-150 |
| **Total Build** | | **$640-950** |
| + Installation Service | Guided setup | $500 |
| **Package Total** | | **$1,140-1,450** |

### Capabilities
- ✅ 7B-14B parameter models (Qwen2.5-7B, Llama-3-8B)
- ✅ Basic voice pipeline (Whisper small/medium)
- ✅ RAG with document retrieval
- ✅ ChatGPT-style web interface
- ⚠️ ~30 tokens/second generation (functional but not snappy)
- ❌ Not suitable for real-time voice agents

### Ideal For
- Solo lawyers reviewing documents
- Individual content creators
- Developers learning local AI
- Privacy-conscious personal use

---

## Tier 2: Prosumer ($2,000-3,000)

### What's Included
| Component | Specification | Estimated Cost |
|-----------|--------------|----------------|
| GPU | RTX 4070 Ti Super 16GB | $750-850 |
| CPU | Intel i7-13700 / Ryzen 7 7700X | $300-380 |
| RAM | 64GB DDR5 | $180-220 |
| Storage | 1TB NVMe Gen4 | $90-120 |
| PSU | 750W 80+ Gold | $100-130 |
| Case + Cooling | Quality mid-tower | $150-200 |
| **Total Build** | | **$1,570-1,900** |
| + Full Setup Service | Hardware + install + 30 days support | $1,500 |
| **Package Total** | | **$3,070-3,400** |

### Capabilities
- ✅ 32B parameter models (Qwen2.5-32B-AWQ)
- ✅ Full voice pipeline (Whisper medium + Kokoro TTS)
- ✅ Real-time voice agents (~2s latency)
- ✅ Advanced RAG with embeddings
- ✅ ~50-60 tokens/second generation
- ✅ 5-8 concurrent users comfortably

### Ideal For
- Small law firms (2-5 attorneys)
- Healthcare practices needing HIPAA compliance
- Small marketing/content teams
- Startups with privacy requirements

---

## Tier 3: Pro ($4,000-6,000)

### What's Included
| Component | Specification | Estimated Cost |
|-----------|--------------|----------------|
| GPU | RTX 4090 24GB | $1,800-2,000 |
| CPU | Intel i9-14900K / Ryzen 9 7950X | $450-550 |
| RAM | 128GB DDR5 | $350-450 |
| Storage | 2TB NVMe Gen4 | $150-200 |
| PSU | 1000W 80+ Platinum | $180-220 |
| Case + AIO Cooling | Premium tower + liquid cooling | $300-400 |
| **Total Build** | | **$3,230-3,820** |
| + Full Setup Service | | $1,500 |
| **Package Total** | | **$4,730-5,320** |

### Capabilities
- ✅ 70B parameter models (Llama-3-70B-AWQ, Qwen2.5-72B-AWQ)
- ✅ Near-GPT-4 quality responses on many tasks
- ✅ Multiple simultaneous model instances
- ✅ Production voice agents (10-20 concurrent, <2s latency)
- ✅ Full RAG + embeddings + voice stack
- ✅ ~80-100 tokens/second generation
- ✅ n8n workflow automation included

### Ideal For
- Mid-size firms (5-15 people)
- Companies replacing $500+/month in API costs
- Internal AI tools for departments
- Customer service automation pilots

---

## Tier 4: Enterprise ($12,000-18,000)

### What's Included
| Component | Specification | Estimated Cost |
|-----------|--------------|----------------|
| GPUs | 2x RTX 4090 24GB | $3,600-4,000 |
| CPU | Intel Xeon or Threadripper | $800-1,200 |
| RAM | 256GB DDR5 ECC | $800-1,000 |
| Storage | 4TB NVMe RAID | $400-500 |
| PSU | 1500W 80+ Titanium | $300-400 |
| Chassis | Rackmount or workstation | $500-800 |
| Cooling | Custom loop or enterprise | $400-600 |
| **Total Build** | | **$6,800-8,500** |
| + Enterprise Setup | Custom integration + SLA | $3,000-5,000 |
| **Package Total** | | **$9,800-13,500** |

### Capabilities
- ✅ 70B models at FP16 (no quantization quality loss)
- ✅ Multiple 32B+ models running simultaneously
- ✅ **20-40 concurrent voice agents** (per our benchmarks)
- ✅ 100+ concurrent chat users
- ✅ Model A/B testing in production
- ✅ Redundancy (one GPU can serve while other is updated)
- ✅ ~150-200 tokens/second combined throughput

### Ideal For
- Organizations with 20+ AI users
- Customer-facing AI deployments
- Companies with regulatory requirements (HIPAA, SOC2)
- Teams running multiple AI applications

---

## Capability Matrix

| Feature | Entry | Prosumer | Pro | Enterprise |
|---------|---------|--------------|----------|------------|
| **Max Model Size** | 14B | 32B | 70B | 70B FP16 |
| **Token Speed** | ~30/s | ~55/s | ~90/s | ~175/s |
| **Voice Agents** | Basic | Real-time | Production | Scale |
| **Concurrent Voice** | 1-2 | 3-5 | 10-20 | 20-40+ |
| **Concurrent Chat** | 1-3 | 5-8 | 15-25 | 50-100+ |
| **RAG/Embeddings** | ✅ | ✅ | ✅ | ✅ |
| **Image Generation** | ⚠️ Slow | ✅ | ✅ Fast | ✅ Fastest |
| **Multi-Model** | ❌ | ⚠️ | ✅ | ✅ |
| **API Endpoints** | ✅ | ✅ | ✅ | ✅ |
| **Web Interface** | ✅ | ✅ | ✅ | ✅ |
| **Workflow Automation** | Basic | Full | Full | Full + Custom |

### Voice Agent Benchmark Reference
*From our production testing on dual RTX setup:*

| Response Target | Single 4090 | Dual 4090 |
|-----------------|-------------|-----------|
| <2 second (voice-ready) | 10-20 users | 20-40 users |
| <5 second (chat-acceptable) | ~50 users | ~100 users |
| Batch/async | 100+ | 200+ |

---

## Monthly Operating Costs

### Power Consumption

| Tier | GPU TDP | System Total | Monthly kWh* | Cost @ $0.12/kWh |
|------|---------|--------------|--------------|------------------|
| Entry | 170W | ~250W | 180 kWh | **$22/mo** |
| Prosumer | 285W | ~400W | 288 kWh | **$35/mo** |
| Pro | 450W | ~600W | 432 kWh | **$52/mo** |
| Enterprise | 900W | ~1,100W | 792 kWh | **$95/mo** |

*Assumes 24/7 operation at 80% average load

### Maintenance Budget

| Tier | Annual Maintenance | Monthly Equivalent |
|------|-------------------|-------------------|
| Entry | ~$100 (thermal paste, fans) | ~$8/mo |
| Prosumer | ~$150 | ~$12/mo |
| Pro | ~$250 | ~$21/mo |
| Enterprise | ~$500 (+ spare parts reserve) | ~$42/mo |

### Total Monthly Operating Cost

| Tier | Power | Maintenance | **Total** |
|------|-------|-------------|-----------|
| Entry | $22 | $8 | **$30/mo** |
| Prosumer | $35 | $12 | **$47/mo** |
| Pro | $52 | $21 | **$73/mo** |
| Enterprise | $95 | $42 | **$137/mo** |

---

## ROI Analysis: Local vs. Cloud APIs

### Cloud API Pricing Reference
*As of February 2026:*

| Provider | Input Cost | Output Cost | Average |
|----------|-----------|-------------|---------|
| OpenAI GPT-4 | $0.03/1K tokens | $0.06/1K tokens | ~$0.04/1K |
| OpenAI GPT-4o | $0.01/1K tokens | $0.03/1K tokens | ~$0.02/1K |
| Anthropic Claude 3.5 | $0.015/1K tokens | $0.075/1K tokens | ~$0.03/1K |
| Google Gemini Pro | $0.00125/1K tokens | $0.005/1K tokens | ~$0.003/1K |

**Blended average for premium models: $0.01-0.03 per 1K tokens**

### Usage Scenarios & Break-Even Analysis

#### Scenario A: Solo Power User
- **Usage:** 500K tokens/day = 15M tokens/month
- **Cloud Cost:** 15M × $0.02/1K = **$300/month**
- **Dream Server (Prosumer):** $47/month operating + $3,200 one-time
- **Break-even:** 3,200 ÷ (300-47) = **12.6 months**
- **Year 2+ Savings:** ~$3,000/year

#### Scenario B: Small Team (5 people)
- **Usage:** 2M tokens/day = 60M tokens/month  
- **Cloud Cost:** 60M × $0.02/1K = **$1,200/month**
- **Dream Server (Pro):** $73/month operating + $5,000 one-time
- **Break-even:** 5,000 ÷ (1,200-73) = **4.4 months**
- **Year 2+ Savings:** ~$13,500/year

#### Scenario C: Production Voice Agents
- **Usage:** 100 voice calls/day × 5K tokens/call = 15M tokens/month
- **Cloud Cost:** 15M × $0.025/1K = **$375/month** (+ Whisper/TTS fees ~$200/month)
- **Dream Server (Pro):** $73/month + $5,000 one-time
- **Break-even:** 5,000 ÷ (575-73) = **10 months**
- **Year 2+ Savings:** ~$6,000/year

#### Scenario D: Enterprise Deployment
- **Usage:** 10M tokens/day = 300M tokens/month
- **Cloud Cost:** 300M × $0.02/1K = **$6,000/month**
- **Dream Server (Enterprise):** $137/month operating + $13,000 one-time
- **Break-even:** 13,000 ÷ (6,000-137) = **2.2 months**
- **Year 2+ Savings:** ~$70,000/year

### ROI Summary Table

| Tier | Monthly Cloud Equivalent | Monthly Operating | Break-Even | Year 2 Savings |
|------|-------------------------|-------------------|------------|----------------|
| Entry | $150-300 | $30 | 8-12 months | $1,500-3,000 |
| Prosumer | $300-600 | $47 | 6-12 months | $3,000-6,500 |
| Pro | $600-1,500 | $73 | 4-8 months | $6,500-17,000 |
| Enterprise | $2,000-8,000 | $137 | 2-6 months | $22,000-95,000 |

---

## Hidden Value: What Cloud Can't Offer

Beyond direct cost savings:

### 1. **Zero Data Exposure**
- Your data never leaves your network
- No third-party processing agreements needed
- Simplified HIPAA/SOC2/GDPR compliance

### 2. **No Rate Limits**
- Cloud APIs throttle during peak usage
- Local: Your capacity, your priority

### 3. **Predictable Costs**
- Cloud bills can spike unexpectedly
- Local: Fixed operating cost regardless of usage

### 4. **Model Freedom**
- Run any open-source model
- Fine-tune on proprietary data
- No vendor lock-in

### 5. **Latency**
- Cloud: 200-500ms network overhead
- Local: Sub-100ms first token

---

## Service Packages

| Package | Price | What's Included |
|---------|-------|-----------------|
| **DIY (Open Source)** | Free | Scripts, docs, community Discord |
| **Guided Install** | $500 | 2-hour session, we configure your hardware |
| **Full Setup** | $1,500 | Hardware recommendations + remote install + 30 days support |
| **Enterprise** | Custom | On-site options, custom integrations, SLA, training |

### Optional Add-Ons
| Add-On | Price | Description |
|--------|-------|-------------|
| Hardware Procurement | 10% markup | We source and ship components |
| Extended Support | $200/month | Priority support, updates, monitoring |
| Custom Workflows | $150/hour | n8n automation, integrations |
| Training Session | $500 | 3-hour team training on local AI tools |

---

## Quick Reference for Sales Calls

### Qualifying Questions
1. "How much are you currently spending on AI APIs monthly?"
2. "How many people on your team use AI tools regularly?"
3. "Do you have data privacy or compliance requirements?"
4. "Do you have IT capacity to maintain a server, or do you need managed?"

### Objection Handling

**"We're happy with ChatGPT/Claude"**
→ "Great tools! Dream Server isn't a replacement—it's for when you need privacy, cost control, or custom models. Many clients use both."

**"Seems expensive upfront"**
→ "The hardware pays for itself in 3-6 months if you're spending $500+/month on APIs. After that, it's essentially free AI."

**"We don't have technical staff"**
→ "That's what our Full Setup service is for. We handle everything and provide 30 days of support. After that, it just runs."

**"What about model updates?"**
→ "Open-source models update constantly—often better than closed models now. We include update procedures, or our support plan handles it."

### Tier Recommendation Quick Guide

| If they say... | Recommend |
|----------------|-----------|
| "Just me, want to try it" | Entry + DIY |
| "Small team, real use case" | Prosumer + Full Setup |
| "Replacing serious API spend" | Pro + Full Setup |
| "Organization-wide rollout" | Enterprise + Custom |
| "Privacy is critical" | Any tier + emphasize local-only |
| "Voice agents / customer service" | Pro or Enterprise |

---

## Competitive Positioning

| vs. | Dream Server Advantage |
|-----|----------------------|
| OpenAI/Anthropic APIs | Privacy, no rate limits, predictable costs |
| Azure/AWS AI Services | Simpler, cheaper, no cloud lock-in |
| Ollama (DIY) | Turnkey, includes voice/RAG/workflows |
| LocalAI | Production-ready stack, not just inference |
| RunPod/Lambda | Own vs rent, no hourly fees |

---

*Document version: 2026-02-10*
*For internal sales use — Light Heart Labs*
