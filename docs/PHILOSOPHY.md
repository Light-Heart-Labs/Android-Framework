# Building Persistent Agent Teams — Philosophy and Patterns

This is the conceptual foundation for everything in this repository. Read this
first. It explains the principles behind the tools, the failure modes they
prevent, and how to apply these patterns to any agent framework — not just
OpenClaw.

The patterns documented here were discovered by running persistent AI agent
teams on local hardware 24/7. Not simulated, not theoretical — three AI agents
writing code, reviewing each other's work, and shipping software, supervised
by a fourth. Every lesson in this repo was learned the hard way, often by the
agents themselves.

---

## The Core Idea

A persistent agent is not a chatbot. A chatbot processes a request and
forgets. A persistent agent works across hours, days, and weeks. It
accumulates knowledge, coordinates with other agents, and operates
infrastructure it depends on.

This changes everything about how you build and operate them.

Chatbots fail gracefully — the conversation ends, the user starts over.
Persistent agents fail silently — they drift from their role, corrupt their
own configuration, exhaust their context window, or coordinate with other
agents based on assumptions nobody verified. By the time you notice, the
damage compounds.

This repository is a methodology for preventing that. It includes a reference
implementation using OpenClaw and vLLM, but the patterns apply to any
framework: Claude Code, LangChain, AutoGPT, custom agents, or anything else
that runs long enough to accumulate state.

---

## Five Pillars

Every pattern in this repo maps to one of five principles. If you understand
these, you understand the entire system.

### 1. Identity — Agents need a constitution, not just a prompt

A persistent agent's identity must survive session resets, context overflow,
and the agent's own attempts to modify it. This means:

- **Baselines** — A curated document defining who the agent is, what rules it
  follows, and what tools it has. Stored above a `---` separator in MEMORY.md.
  The agent can read it but must not modify it.
- **Periodic resets** — Every few hours, scratch notes get archived and the
  baseline is restored. The agent starts fresh but knows who it is.
- **Operator control** — The human defines identity. The agent operates within
  it. This separation is the most important architectural decision you'll make.

Without identity preservation, agents drift. They accumulate stale context,
adopt instructions from previous tasks, and gradually become something other
than what you built. The drift is subtle — you won't notice for hours or days.

**Deep dive:** [WRITING-BASELINES.md](../memory-shepherd/docs/WRITING-BASELINES.md)
and [Memory Shepherd](../memory-shepherd/README.md)

### 2. Knowledge — Three tiers of persistence, not one

Agents need memory at three timescales, each with different durability:

| Tier | What | Lifetime | Where |
|------|------|----------|-------|
| Scratch | Working notes for the current task | Hours (until next reset) | Below `---` in MEMORY.md |
| Daily | What happened today, raw observations | Days to weeks | `memory/YYYY-MM-DD.md` |
| Permanent | Architecture decisions, lessons learned | Forever | Project repo, baselines, docs |

The critical insight: **nothing important should live only in scratch notes.**
Agents must be taught to externalize knowledge upward through the tiers before
a reset wipes their scratch space. Include an explanation of the memory system
in the baseline itself — agents that understand their own memory lifecycle
write better notes and preserve the right things.

Without tiered persistence, agents either lose everything on reset (too
aggressive) or accumulate unbounded state until they crash (too permissive).
Three tiers give you the best of both: clean working memory AND durable
learning.

**Deep dive:** [OPERATIONAL-LESSONS.md](OPERATIONAL-LESSONS.md) (session and
memory management section)

### 3. Collaboration — Explicit protocols, not implicit coordination

Multiple agents sharing a codebase will overwrite each other's work, amplify
each other's assumptions, and celebrate phantom success — unless you give them
explicit rules for coordination.

The three protocols that matter:

- **Branch-based review** — Code changes go through feature branches with
  agent-identifiable prefixes. A separate agent reviews and merges. Docs and
  status updates go direct to main.
- **Heartbeat sync** — Every 15-60 minutes, each agent pulls latest, checks
  for pending work and reviews, and updates its status. This prevents drift
  between agents and catches handoffs that would otherwise sit idle.
- **Echo chamber prevention** — When agents agree too fast, nobody is
  verifying. The rule: one lead investigator for debugging, independent
  verification before claiming success, pause when messages fly too fast.

Without explicit protocols, multi-agent systems develop the same dysfunctions
as human teams — except faster, because agents don't get tired and don't
second-guess themselves.

**Deep dive:** [MULTI-AGENT-PATTERNS.md](MULTI-AGENT-PATTERNS.md)

### 4. Autonomy — Tiered permissions, not all-or-nothing trust

Agents need to know exactly what they can do freely, what needs a second
opinion, and what requires human approval. The tiers:

| Tier | Rule | Examples |
|------|------|---------|
| 0 — Just do it | Low risk, high frequency | Read files, run tests, push to feature branches, write scratch notes |
| 1 — Peer review | Medium risk | Config changes, new tools, research conclusions before sharing |
| 2 — Escalate | High risk, irreversible | Production systems, external communications, spending money |

The principle: **minimize the permission surface at each tier.** If an agent
can do its job with Tier 0 permissions 90% of the time, it should rarely need
to escalate. If it's constantly hitting Tier 2, either the tiers are wrong or
the agent's role is too broad.

Vague rules ("be careful") don't work. Specific rules do ("never push directly
to main," "never modify another agent's MEMORY.md"). Write 5-7 hard
boundaries, not 50 guidelines.

**Deep dive:** [GUARDIAN.md](GUARDIAN.md) (autonomy tiers section)

### 5. Observability — You can't manage what you can't measure

Persistent agents fail in ways that are invisible without instrumentation:

- Context fills silently until it overflows
- Costs accumulate with no per-turn visibility
- Agents get stuck but the process keeps running
- Quality degrades gradually as context gets stale

You need two kinds of monitoring:

- **Cost monitoring** (Token Spy) — What are you spending? Per-turn, per-agent,
  per-session. Catches retry loops, runaway costs, and dead agents (zero cost
  on a cloud agent means it stopped working, not that it's efficient).
- **Infrastructure monitoring** (Prometheus/Grafana) — Is the GPU overloaded?
  Are services healthy? What's the queue depth? Catches resource contention,
  service crashes, and capacity limits.

These measure different things and will diverge. A local model shows $0 in
Token Spy but heavy load in GPU metrics. A cached response shows reduced cost
but no GPU activity. Both views are necessary.

Add a **supervisor agent** — a meta-agent that monitors the team rather than
doing work. It checks commit frequency, session health, and error patterns
every 15 minutes, and sends the human a daily briefing. The supervisor is
judgment, not volume — run it on the most capable model you have.

**Deep dive:** [TOKEN-SPY.md](TOKEN-SPY.md), [OPERATIONAL-LESSONS.md](OPERATIONAL-LESSONS.md)
(monitoring section), [MULTI-AGENT-PATTERNS.md](MULTI-AGENT-PATTERNS.md)
(supervisor pattern)

---

## What Breaks and Why

Every pattern in this repo exists because something broke. Here's the full
failure taxonomy, organized by what goes wrong and what prevents it.

### Session-Level Failures — Agents Stop Working

| Failure | What Happens | Prevention |
|---------|-------------|-----------|
| Context overflow | Session grows until it exceeds the model's context window. Agent crashes with "prompt too large." | Session Watchdog monitors file size, transparently swaps in fresh sessions before overflow. |
| Memory bloat | Scratch notes accumulate, degrading response quality. Agent confuses past and present tasks. | Memory Shepherd archives scratch notes and resets to baseline every 3 hours. |
| Identity drift | Agent gradually shifts behavior as old context influences new decisions. Sometimes rewrites its own instructions. | Baseline separation (`---` contract). Operator-controlled identity above the line, agent scratch space below. |
| Cost spike | Agent enters a retry loop or spawns too many cloud sub-agents. Burns through API budget. | Token Spy tracks per-turn cost. Auto-resets sessions that exceed character limits. |

### Coordination Failures — Agents Fight Each Other

| Failure | What Happens | Prevention |
|---------|-------------|-----------|
| Merge conflicts | Multiple agents modify the same files simultaneously. | Branch-based review protocol. Agent-prefixed branches. One merger. |
| Echo chamber | Agents agree without verifying. Celebrate success when files don't exist. | One-lead rule. Independent verification. Pause on rapid-fire messages. |
| State races | Two agents read the same status file, both claim the same task. | Heartbeat protocol with explicit claiming. STATUS.md as coordination point. |
| Phantom completion | Agent reports "done" before verifying the work actually happened. | "Working tree state > status reports." Verify files exist, tests pass, commits landed. |

### Infrastructure Failures — The System Breaks

| Failure | What Happens | Prevention |
|---------|-------------|-----------|
| Service crash | Gateway, proxy, or vLLM goes down. Agent appears stuck. | Guardian watchdog monitors all services. 3-strike auto-recovery. |
| Config corruption | Agent modifies a config it depends on. Silent failures. | Immutable files (`chattr +i`). Checksum validation. Guardian restores from backup. |
| Self-sabotage | Agent kills its own gateway while debugging, or modifies the proxy it routes through. | Autonomy tiers. Self-modification rule: never hot-work your own infrastructure. |
| GPU contention | Multiple agents flood the GPU with sub-agent requests. One agent's requests time out, session gets stuck. | Custom health checks detect timeout + cleared storm pattern. Guardian auto-restarts stuck gateways. |

### Knowledge Failures — Lessons Get Lost

| Failure | What Happens | Prevention |
|---------|-------------|-----------|
| Scratch notes wiped | Important findings live only in scratch space. Reset deletes them. | Three-tier persistence. Teach agents to externalize upward before resets. |
| Baseline stale | Agent's role changes but baseline doesn't. Agent rediscovers context every reset. | Regular baseline review. If the agent keeps rediscovering the same thing, add it to the baseline. |
| No shared learning | Each agent discovers the same problems independently. No collective memory. | Shared lessons file (append-only, date-attributed). Daily logs distilled into permanent knowledge. |

---

## Reading Map

### "I'm building a single persistent agent"

Start here, then read in order:

1. [WRITING-BASELINES.md](../memory-shepherd/docs/WRITING-BASELINES.md) —
   How to define your agent's identity
2. [Memory Shepherd README](../memory-shepherd/README.md) — How memory resets work
3. [SETUP.md](SETUP.md) — Getting the infrastructure running (OpenClaw-specific)
4. [OPERATIONAL-LESSONS.md](OPERATIONAL-LESSONS.md) — What will go wrong
   and how to fix it

### "I'm running multiple agents together"

Read the single-agent path first, then:

5. [MULTI-AGENT-PATTERNS.md](MULTI-AGENT-PATTERNS.md) — Coordination,
   swarms, redundancy, the supervisor pattern
6. [cookbook/06-swarm-patterns.md](cookbook/06-swarm-patterns.md) — Hands-on
   sub-agent spawning patterns with code examples
7. [GUARDIAN.md](GUARDIAN.md) — Infrastructure protection and autonomy tiers

### "I want to build something specific"

Browse the [Cookbook](cookbook/README.md) — step-by-step recipes for voice
agents, document Q&A, code assistants, multi-GPU clusters, and more.

### "I want to understand the theory without building anything"

Read this document, then:

1. [WRITING-BASELINES.md](../memory-shepherd/docs/WRITING-BASELINES.md) —
   The deepest treatment of identity and memory
2. [MULTI-AGENT-PATTERNS.md](MULTI-AGENT-PATTERNS.md) — Coordination
   theory, reliability math, and failure modes
3. [GUARDIAN.md](GUARDIAN.md) — The philosophy of infrastructure
   self-defense

### "I need to fix something that's broken right now"

Go to the [failure taxonomy](#what-breaks-and-why) above. Find your symptom.
Follow the link to the prevention strategy.

---

## Using These Patterns With Other Frameworks

About 70% of this repo is framework-agnostic. Here's what applies where.

### Universal Patterns (any agent framework)

These patterns work regardless of whether you use OpenClaw, Claude Code,
LangChain, AutoGPT, or custom agents:

| Pattern | Core Idea | Adapt By |
|---------|-----------|----------|
| **Baseline identity** | Agent has a constitution that survives resets | Store in system prompt, config file, or persistent state — whatever your framework reads on startup |
| **Memory tiers** | Scratch / daily / permanent knowledge layers | Implement file-based persistence at each tier. The storage mechanism doesn't matter; the separation does. |
| **Autonomy tiers** | Tiered permissions (do freely / peer review / escalate) | Encode in the agent's system prompt or baseline. No framework support needed — it's behavioral. |
| **Branch-based review** | Code changes through feature branches with review gates | Use Git conventions. Framework-independent. |
| **Heartbeat protocol** | Periodic sync, status checks, handoff detection | Implement as a cron job, scheduled task, or supervisor loop |
| **Echo chamber prevention** | One lead, independent verification, pause on rapid-fire | Behavioral rules in agent baselines. No code required. |
| **Supervisor agent** | Meta-agent that monitors team health and briefs the human | Any agent that can read logs, check file sizes, and send messages |
| **Redundancy math** | Spawn 2 agents, take first success: 67% → 95% reliability | Any system that can run parallel tasks |
| **Task templates** | Numbered steps, absolute paths, stop prompts | Universal prompt engineering. Works with any LLM. |
| **Guardian / watchdog** | Immutable process that monitors and auto-recovers services | Bash script + systemd (or equivalent). Framework-independent. |
| **Failure taxonomy** | Categorized failure modes with mapped preventions | Apply the categories to your system. The failures are universal. |

### OpenClaw / vLLM Specific

These solve problems unique to the OpenClaw + vLLM stack:

| Component | What It Solves | Equivalent In Other Frameworks |
|-----------|---------------|-------------------------------|
| Tool proxy | OpenClaw streams; vLLM needs non-streaming for tool extraction | Not needed if your framework handles tool calling natively |
| Session watchdog | Monitors `.jsonl` session files for size | Adapt to your framework's session storage format |
| Compat block | Prevents OpenClaw from sending params vLLM rejects | Not needed for cloud APIs or frameworks with native vLLM support |
| Token Spy | Transparent reverse proxy for API cost monitoring | Works with any OpenAI-compatible or Anthropic client — already portable |

### Translation Guide

**Claude Code agents:** Store baselines in CLAUDE.md or a persistent context
file. Use the autonomy tiers as behavioral instructions in the system prompt.
Run Memory Shepherd against whatever file your agent uses for persistent state.
Token Spy already works with Claude's API via `ANTHROPIC_BASE_URL`.

**LangChain / LlamaIndex agents:** Store baselines in the agent's
initialization config. Implement the three-tier memory pattern using the
framework's memory modules. The coordination protocols (branches, heartbeat)
are Git-level, not framework-level.

**Custom Python agents:** Store baselines in a config file loaded at startup.
Implement Memory Shepherd's reset cycle as a function that reads the file,
splits on `---`, archives the bottom, restores the top. The Guardian is a
standalone bash script — it doesn't care what framework the agents use.

---

## How This Repo Is Organized

```
PHILOSOPHY.md (you are here)
  │
  ├── Identity & Memory
  │     ├── memory-shepherd/README.md        — How memory resets work
  │     └── memory-shepherd/docs/
  │           └── WRITING-BASELINES.md       — How to define agent identity
  │
  ├── Coordination & Operations
  │     ├── MULTI-AGENT-PATTERNS.md          — Sync, swarms, supervisor, reliability
  │     └── OPERATIONAL-LESSONS.md           — Battle-tested lessons from 24/7 ops
  │
  ├── Infrastructure & Safety
  │     └── GUARDIAN.md                      — Watchdogs, autonomy tiers, protection
  │
  ├── Cookbook (cookbook/)                     — Step-by-step build recipes
  │     ├── 01-voice-agent-setup.md          — Whisper + vLLM + Kokoro pipeline
  │     ├── 05-multi-gpu-cluster.md          — Multi-GPU cluster guide
  │     └── 06-swarm-patterns.md             — Sub-agent parallelization patterns
  │
  ├── Research (research/)                   — Benchmarks and hardware analysis
  │     ├── HARDWARE-GUIDE.md                — GPU buying guide
  │     └── OSS-MODEL-LANDSCAPE-2026-02.md   — Open-source model comparison
  │
  └── Reference Implementation (OpenClaw + vLLM)
        ├── README.md                        — Toolkit overview and quick start
        ├── ARCHITECTURE.md                  — How OpenClaw talks to vLLM
        ├── SETUP.md                         — Step-by-step local deployment
        ├── TOKEN-SPY.md                     — Cost monitoring setup and API
        └── TOKEN-MONITOR-PRODUCT-SCOPE.md   — Token Spy product roadmap
```

The top three sections are framework-agnostic. The reference implementation
section is OpenClaw-specific but demonstrates the patterns concretely.

---

## The Meta-Lesson

The single most important pattern in this repo isn't a tool or a script. It's
this: **agents will find every edge case you didn't think of, and the only
reliable documentation is the post-mortems they write after hitting those
edges.**

Build a shared lessons file. Make it append-only. Date every entry. Have
agents write to it when they discover something the hard way. Review it
periodically and promote the important lessons into baselines and permanent
docs.

The tools in this repo prevent the catastrophic failures. The lessons file
captures everything else. Together, they compound — each week, the system gets
a little more robust, the baselines get a little more complete, and the agents
get a little more reliable.

That's the real goal: not a system that never fails, but a system that learns
from every failure and gets better.

---

Built from production experience by [Lightheart Labs](https://github.com/Light-Heart-Labs)
and their AI agent team. The patterns were discovered by the agents. The docs
were written by the agents. The lessons were learned the hard way.
