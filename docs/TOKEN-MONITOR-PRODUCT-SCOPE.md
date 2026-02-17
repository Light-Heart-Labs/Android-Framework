# Token Spy — Product Scope & Roadmap
*(formerly OpenClaw Token Monitor)*

## Executive Summary

OpenClaw Token Monitor is a **transparent API proxy** that captures per-request token usage, cost, and session health metrics for LLM-powered agents — with **zero code changes** to downstream applications. It currently runs as a personal tool monitoring two AI agents across two LLM providers (Anthropic, Moonshot/Kimi).

This document scopes the path from personal tool to commercial product, targeting developers and teams running LLM-powered agents, workflows, and applications who need visibility into what they're spending, where, and why.

---

## Core Value Proposition

**"See everything your AI spends. Change nothing in your code."**

Unlike SDK-based observability tools (LangSmith, Langfuse, W&B Weave) that require instrumenting every call site, and unlike competing proxy tools (Helicone, Portkey) that still require a base URL change and auth header, OpenClaw Token Monitor operates as a truly transparent proxy — point your agent's traffic through it and every LLM interaction is automatically captured, analyzed, and visualized.

### Why This Matters

- **Zero integration friction** — No SDK, no framework lock-in, no code changes. Works with any language, any LLM client library, any agent framework.
- **Session intelligence** — Not just request logging. Understands conversation arcs, detects session boundaries, tracks context window growth, and recommends when to reset.
- **Prompt cost attribution** — Breaks down what's actually eating tokens: system prompt components, workspace files, skill injections, conversation history. No other tool does this at the proxy level.
- **Operational safety** — Auto-resets runaway sessions before they burn through budgets. Acts as both observer and guardrail.

---

## Competitive Landscape

| Tool | Approach | Integration Effort | Strengths | Weakness vs. Us |
|------|----------|-------------------|-----------|-----------------|
| **Helicone** | Proxy gateway (Rust/CF Workers) | Base URL + API key header change | Mature, open source, 2B+ interactions | Still requires code change; no session intelligence |
| **Portkey** | AI gateway | Base URL change + SDK optional | 200+ providers, guardrails, enterprise governance | Heavy/complex; no prompt-level cost attribution |
| **Langfuse** | SDK instrumentation | SDK integration per call site | Open source, deep tracing, self-hostable | Framework coupling; maintenance burden |
| **LangSmith** | SDK (LangChain native) | LangChain/LangGraph integration | Deep chain tracing, evaluation | Ecosystem lock-in; useless outside LangChain |
| **Datadog LLM** | SDK instrumentation | Python SDK + Datadog agent | Integrates with existing infra monitoring | Enterprise pricing; Python-only; heavy stack |
| **Groundcover** | eBPF kernel-level | Zero (but K8s + eBPF required) | Truly zero instrumentation | K8s-only; no session awareness; infrastructure-focused |
| **Braintrust** | SDK + eval platform | SDK integration | Strong evaluation/scoring | Evaluation-first, not operations-first |

### Our Differentiated Position

1. **Transparent proxy** — zero code changes, works in any environment (not just K8s)
2. **Session-aware intelligence** — conversation arc tracking, auto-reset, cache efficiency analysis
3. **Prompt cost decomposition** — see exactly which parts of your system prompt are costing money
4. **Operational safety rails** — budget enforcement and runaway session protection built into the proxy layer

---

## What Exists Today

### Current Architecture
```
Agent-A ──► Proxy ──► api.anthropic.com
Agent-B ──► Proxy ──► api.moonshot.ai
                │
           SQLite DB (usage.db)
                │
           Dashboard (served by proxy)
```

### Current Capabilities
- Transparent proxy for Anthropic Messages API and OpenAI-compatible Chat Completions API
- SSE streaming passthrough with zero buffering
- Per-turn logging: model, tokens (input/output/cache_read/cache_write), cost, latency, stop reason
- Request analysis: message count by role, tool count, request body size
- System prompt decomposition: workspace files (AGENTS.md, SOUL.md, etc.), skill injections, base prompt
- Conversation history char tracking across turns
- Session boundary detection (history drop = new session)
- Session health scoring with recommendations (healthy → monitor → compact_soon → reset_recommended → cache_unstable)
- Auto-reset safety valve (kills sessions exceeding 200K chars)
- External session manager (cron job, cleans inactive sessions, enforces count limits)
- Dashboard: summary cards, cost-per-turn timeline, history growth chart, token usage bars, cost breakdown doughnut, cumulative cost, recent turns table, session health panels with reset buttons
- Cost estimation with per-model pricing tables (8 Claude variants, 4 Kimi variants)
- Protocol translation (OpenAI `developer` role → `system` for Kimi compatibility)

### Current Limitations
- Single-user, hardcoded agent names and session directories
- Two providers only (Anthropic, Moonshot), each requiring a separate handler
- SQLite with thread-local connections (single-node only)
- Dashboard is inline HTML in main.py (no component framework, no auth)
- No alerting, no budgets, no API keys for the proxy itself
- No data export, no retention policies, no multi-node deployment

---

## Product Roadmap

### Phase 1: Foundation (Weeks 1–6)
**Goal: Multi-user, multi-provider proxy that anyone can self-host.**

#### 1.1 Provider Plugin System
Generalize the two existing proxy handlers into a provider adapter interface.

- **Provider adapter contract**: Each provider implements `parse_request()`, `forward_streaming()`, `forward_sync()`, `extract_usage()`, `estimate_cost()`
- **Built-in adapters**: Anthropic Messages API, OpenAI Chat Completions API (covers OpenAI, Azure OpenAI, Moonshot/Kimi, Groq, Together, Fireworks, DeepSeek, any OpenAI-compatible)
- **Google Vertex/Gemini adapter**: Third priority given market share
- **Configuration-driven**: Provider endpoints, cost tables, and model mappings defined in YAML/TOML config, not code
- **Custom cost tables**: Users override per-model pricing to match their negotiated rates or fine-tuned model costs

```yaml
providers:
  anthropic:
    base_url: https://api.anthropic.com
    adapter: anthropic_messages
    models:
      claude-sonnet-4:
        input: 3.00
        output: 15.00
        cache_read: 0.30
        cache_write: 3.75

  openai:
    base_url: https://api.openai.com
    adapter: openai_chat
    models:
      gpt-4o:
        input: 2.50
        output: 10.00
```

#### 1.2 Multi-Tenancy & Auth
- **Proxy API keys**: Customers generate keys that authenticate requests to the proxy. The proxy maps keys to tenants and attaches metadata (tenant, agent, environment) to every logged request.
- **Tenant isolation**: All queries scoped by tenant. No cross-tenant data leakage.
- **Dashboard auth**: Session-based login for the web dashboard. Each tenant sees only their data.
- **Provider key management**: Customers register their own provider API keys (encrypted at rest). The proxy injects the correct key when forwarding upstream.

#### 1.3 Database Migration
- **PostgreSQL** as the primary store for transactional data (tenants, API keys, provider configs)
- **TimescaleDB extension** (or ClickHouse) for the usage time-series data — enables fast aggregation queries over large time ranges without manual rollup tables
- **Migration path**: Script to import existing SQLite data
- **Retention policies**: Configurable per-tenant (e.g., raw data for 30 days, hourly rollups for 1 year)

#### 1.4 Configuration & Deployment
- **YAML/TOML config file** replacing all hardcoded values (agent names, thresholds, upstream URLs, cost tables)
- **Docker Compose** for self-hosted deployment (proxy + postgres + dashboard)
- **Environment variable overrides** for 12-factor compatibility
- **Health check endpoints** with dependency status (upstream providers reachable, DB connected)

**Phase 1 Deliverable**: A self-hostable Docker Compose stack that any developer can deploy, create an API key, point their agents at, and immediately see usage data in an authenticated dashboard. Supports any OpenAI-compatible or Anthropic-compatible provider out of the box.

---

### Phase 2: Analytics Dashboard (Weeks 7–12)
**Goal: A real frontend that makes the data actionable.**

#### 2.1 Dashboard Rebuild
- **Next.js + React** frontend (or SvelteKit — lighter weight, good fit for data dashboards)
- **Responsive design** preserving the current dark theme aesthetic
- **Real-time updates** via WebSocket or Server-Sent Events (watch agents work live)
- **Time range picker** with presets (1h, 6h, 24h, 7d, 30d, custom range)
- **Auto-refresh** with configurable interval

#### 2.2 Core Analytics Views

**Overview Dashboard**
- Total spend (period), trend vs. previous period
- Active agents/workflows count
- Request volume and error rate
- Top spenders (by agent, model, provider)
- Cost forecast based on current burn rate

**Agent/Workflow Explorer**
- Per-agent drill-down: cost over time, token distribution, session timeline
- Session replay: step through a session's turns, see cost accumulate, identify expensive turns
- Conversation arc visualization: history growth, cache efficiency over session lifetime
- Compare agents side-by-side (cost efficiency, token patterns, model usage)

**Model Analytics**
- Cost per model over time
- Token efficiency by model (output tokens per dollar)
- Latency distribution by model and provider
- Cache hit rates by model (which models benefit most from prompt caching?)
- Model comparison: "Switching Agent X from Opus to Sonnet would save $Y/day based on last 7 days"

**Prompt Economics**
- System prompt cost attribution: what percentage of input cost goes to system prompt vs. conversation history vs. tool definitions?
- Prompt component breakdown over time (unique to OpenClaw — no competitor has this)
- "Your AGENTS.md file costs $0.003 per turn across 200 turns/day = $0.60/day. Is it worth it?"
- Workspace file size trends — detect prompt bloat early

**Cost & Budget**
- Cumulative cost by any dimension (agent, model, provider, tag, time)
- Budget configuration per agent/team/tag with alerts
- Projected monthly cost based on rolling averages
- Cost anomaly detection (sudden spend spikes)

#### 2.3 Tagging & Metadata
- **Request tags**: Arbitrary key-value metadata attached to requests via HTTP headers (e.g., `X-OpenClaw-Tags: env=prod,workflow=customer-support,team=backend`)
- **Agent auto-detection**: Infer agent identity from API key, request patterns, or explicit header
- **Environment segmentation**: dev/staging/prod cost breakdowns
- **Custom dimensions**: Let users define their own grouping dimensions

**Phase 2 Deliverable**: A polished, real-time analytics dashboard that turns raw telemetry into actionable insights about cost, efficiency, and agent behavior. The prompt economics view is the flagship differentiator.

---

### Phase 3: Intelligence & Automation (Weeks 13–20)
**Goal: The proxy doesn't just observe — it advises and acts.**

#### 3.1 Alerting & Budgets
- **Alert rules**: Configurable triggers on any metric (cost > $X/hour, cache hit rate < Y%, latency > Zms, error rate > N%)
- **Budget enforcement**: Hard and soft limits per agent, team, or tag. Soft = alert. Hard = reject requests with 429.
- **Notification channels**: Email, Slack webhook, PagerDuty, generic webhook
- **Anomaly alerts**: Automatic detection of unusual spending patterns without manual threshold configuration

#### 3.2 Smart Recommendations
Evolve the existing session health recommendations into a broader advisor system:

- **Model routing suggestions**: "Agent X used Opus for 47 turns where average output was <100 tokens. Haiku would handle these at 1/5 the cost." Based on actual usage patterns, not guesses.
- **Cache optimization**: "Your cache hit rate for Agent Y dropped from 95% to 60% after you updated SOUL.md. The new version breaks prefix cache alignment. Here's why."
- **Prompt trimming**: "TOOLS.md accounts for 12K chars of every request but tools are only called in 8% of turns. Consider lazy-loading tool definitions."
- **Session lifecycle**: "Agent X sessions average 45 turns before context window pressure causes quality degradation. Consider auto-compaction at turn 35." (Extension of existing auto-reset logic.)
- **Cost allocation insights**: "80% of your spend is conversation history re-transmission. Aggressive summarization or session splitting would reduce costs by ~40%."

#### 3.3 API & Integrations
- **REST API** for all dashboard data (already partially exists — formalize and version it)
- **OpenTelemetry export**: Push metrics to Datadog, Grafana, New Relic, etc.
- **Prometheus `/metrics` endpoint**: For teams with existing Prometheus/Grafana stacks
- **Webhook on events**: Fire webhooks on session reset, budget exceeded, anomaly detected, etc.
- **CSV/JSON export**: Download usage data for custom analysis

#### 3.4 Session Management (Productize)
Generalize the existing session-manager.sh and auto-reset system:

- **Session lifecycle policies**: Per-agent rules for when to compact, reset, or alert
- **Session cost tracking**: Total cost per session, not just per turn
- **Session quality scoring**: Detect degradation patterns (growing latency, cache thrashing, increasing error rate) as a session ages
- **Manual session controls**: Reset, pause, or throttle agents from the dashboard (already partially exists — polish and generalize)

**Phase 3 Deliverable**: An intelligent proxy that actively helps users reduce costs and improve agent performance, with integrations into existing DevOps tooling.

---

### Phase 4: Enterprise & Scale (Weeks 21–30)
**Goal: Ready for teams and organizations.**

#### 4.1 Multi-User & RBAC
- **Organizations & teams**: Hierarchical structure (org → team → agent)
- **Role-based access**: Admin (full access), Member (view + configure own agents), Viewer (read-only dashboards)
- **SSO**: SAML and OIDC for enterprise identity providers
- **Audit log**: Who changed what configuration, who triggered a session reset, etc.

#### 4.2 Scaling
- **Horizontal proxy scaling**: Stateless proxy instances behind a load balancer (state lives in Postgres/Timescale)
- **Connection pooling**: Replace per-request httpx clients with a managed pool
- **Request queuing**: Optional rate limiting and request queuing to protect upstream providers during traffic spikes
- **Multi-region**: Deploy proxy instances close to users and upstream providers to minimize latency overhead

#### 4.3 Security & Compliance
- **API key encryption**: Vault-backed secret storage for provider API keys
- **TLS everywhere**: mTLS between proxy and upstream providers
- **Request/response redaction**: Option to strip or hash sensitive content before logging (PII protection)
- **SOC 2 Type II** preparation (required for enterprise sales in this space)
- **Data residency**: Per-tenant control over where data is stored

#### 4.4 Advanced Proxy Features
- **Smart routing**: Route requests to the cheapest/fastest provider based on model, latency, and cost rules
- **Automatic fallback**: If Provider A returns 5xx, retry on Provider B transparently
- **Response caching**: Cache identical requests (configurable TTL) to save money on repeated queries
- **Request transformation**: Translate between API formats (e.g., send OpenAI-format requests to Anthropic) — extending the existing developer→system role rewriting

**Phase 4 Deliverable**: Enterprise-ready platform with team management, security compliance, and the proxy features that make it a proper AI gateway (not just an observer).

---

### Phase 5: Platform & Ecosystem (Weeks 31+)
**Goal: From product to platform.**

#### 5.1 Managed Cloud Offering
- **Hosted proxy endpoints**: Customers get a dedicated proxy URL (e.g., `https://yourteam.openclaw.dev/v1/messages`)
- **Usage-based pricing**: Free tier → Pro → Enterprise (see Pricing section)
- **Global edge deployment**: Proxy instances on major cloud regions for low-latency forwarding
- **Uptime SLA**: 99.9% for Pro, 99.95% for Enterprise

#### 5.2 Optional SDK (Deeper Visibility)
For customers who want visibility beyond what a proxy can capture:

- **Lightweight tracing SDK**: Annotate specific code paths with custom spans (e.g., "RAG retrieval took 200ms and returned 5 chunks")
- **Agent framework integrations**: First-class plugins for LangChain, CrewAI, AutoGen, OpenClaw (your own framework)
- **Hybrid mode**: SDK traces merge with proxy telemetry into a unified timeline

#### 5.3 Evaluation & Quality
- **Output scoring**: Attach quality scores to responses (manual or automated via LLM-as-judge)
- **Regression detection**: Alert when output quality drops for a given agent/workflow
- **A/B testing**: Route traffic between model variants and compare cost vs. quality
- **Prompt playground**: Test prompt changes against historical inputs and see projected cost/quality impact

#### 5.4 Community & Marketplace
- **Provider adapter marketplace**: Community-contributed adapters for niche providers
- **Dashboard template sharing**: Pre-built dashboard layouts for common use cases (chatbot monitoring, agent fleet management, batch processing analytics)
- **Open source core**: Core proxy + adapters open source; dashboard, intelligence features, and managed cloud as commercial offerings

---

## Pricing Model (Proposed)

Based on market analysis, the following structure balances adoption friction with revenue:

| Tier | Price | Includes |
|------|-------|----------|
| **Free** | $0 | 10K requests/month, 1 agent, 7-day retention, community support |
| **Pro** | $49/month | 500K requests/month, unlimited agents, 90-day retention, alerts & budgets, email support |
| **Team** | $199/month | 2M requests/month, RBAC (up to 10 seats), 1-year retention, smart recommendations, Slack/webhook alerts |
| **Enterprise** | Custom | Unlimited requests, SSO/SAML, audit logs, custom retention, SLA, dedicated support, on-prem/BYOC option |
| **Self-Hosted** | Free (open source core) | Unlimited, community support only. Commercial add-ons for enterprise features. |

**Why this works:**
- Free tier removes all adoption friction (competitive with Helicone's 10K free, Braintrust's 1M free)
- $49 Pro undercuts Helicone ($79) and Portkey ($49+) while including features they gate behind higher tiers
- Self-hosted option builds trust and community (Langfuse's model proves this works)
- Enterprise tier captures high-value customers who need compliance and SLAs

---

## Technical Architecture (Target State)

```
                    ┌──────────────────────────────┐
                    │       Load Balancer           │
                    │   (nginx / cloud ALB)         │
                    └──────────┬───────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │  Proxy     │   │  Proxy     │   │  Proxy     │
        │  Instance  │   │  Instance  │   │  Instance  │
        │  (FastAPI) │   │  (FastAPI) │   │  (FastAPI) │
        └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │ PostgreSQL │   │ TimescaleDB│   │   Redis    │
        │ (config,   │   │ (usage     │   │ (sessions, │
        │  tenants,  │   │  metrics,  │   │  rate      │
        │  API keys) │   │  time-     │   │  limits,   │
        │            │   │  series)   │   │  cache)    │
        └────────────┘   └────────────┘   └────────────┘
                               │
                        ┌──────▼──────┐
                        │  Dashboard   │
                        │  (Next.js /  │
                        │  SvelteKit)  │
                        └─────────────┘
```

### Key Architectural Decisions

1. **Keep the proxy in Python/FastAPI** — Rewriting in Rust (like Helicone) would reduce latency but massively increase development time. FastAPI with httpx async is fast enough (<10ms overhead) for the initial product. Optimize later if latency becomes a measurable customer concern.

2. **TimescaleDB over ClickHouse** — TimescaleDB is PostgreSQL-compatible (one fewer technology to operate), handles the insert volume we'll see for the first 1000 customers, and supports continuous aggregates for rollup queries. ClickHouse is better at extreme scale but adds operational complexity.

3. **Stateless proxy instances** — All state in the database. Proxy instances can scale horizontally behind a load balancer. Sticky sessions not required.

4. **Provider adapters as Python modules** — Not microservices. A provider adapter is a Python class with 4-5 methods. Loaded at startup based on config. This keeps the deployment simple (one binary/container) while allowing extensibility.

---

## Success Metrics

### Phase 1 (Foundation)
- Self-hosted deployment works in <15 minutes (docker compose up)
- Supports 3+ providers (Anthropic, OpenAI-compatible, Google)
- <15ms proxy overhead at p99

### Phase 2 (Dashboard)
- Dashboard loads in <2 seconds
- Users can answer "how much did Agent X cost this week?" in <10 seconds
- Prompt economics view shows cost attribution data no other tool provides

### Phase 3 (Intelligence)
- Recommendations surface actionable savings (target: median user finds 20%+ cost reduction opportunity within first week)
- Alert→resolution time under 5 minutes for budget breaches
- 3+ integration channels supported (Slack, email, webhook)

### Phase 4 (Enterprise)
- SOC 2 Type II compliant
- Supports 100+ concurrent agents per tenant without degradation
- <5 second query time on 90-day aggregations

### Product-Market Fit Indicators
- Free→Pro conversion rate >5%
- Net revenue retention >120% (teams expand usage over time)
- Weekly active dashboard users >60% of paying customers

---

## Open Questions & Risks

1. **Build vs. contribute**: Helicone is open source. Should we build from scratch or fork/extend Helicone's proxy layer and differentiate on the intelligence/analytics layer?

2. **Python performance ceiling**: FastAPI/httpx adds ~5-10ms overhead. Helicone's Rust proxy adds ~50-80ms (but does more work at the edge). Is our Python advantage real, or will we need Rust eventually?

3. **Prompt decomposition portability**: The current system prompt analysis is tightly coupled to OpenClaw's markdown structure (AGENTS.md, SOUL.md, etc.). How do we generalize this for arbitrary agent frameworks? Possible approach: let users define their own "prompt component" patterns via regex or markers.

4. **Market timing**: The LLM observability market is crowding fast. Speed to market matters more than feature completeness. The MVP should ship the moment Phase 1 + core Phase 2 views are ready.

5. **Self-hosted vs. cloud-first**: Langfuse proved that open-source-first builds community and trust. But cloud-hosted generates revenue faster. Recommendation: open source the core proxy from day one, cloud-host the dashboard and intelligence features.

6. **Naming**: "OpenClaw Token Monitor" describes what it does today. A product name should convey the broader vision. Candidates: "OpenClaw Observatory", "Clawmetrics", or keep "Token Monitor" for its directness.
