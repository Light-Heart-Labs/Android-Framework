# Agent Monitoring Dashboard — Design Doc

**Status:** Draft
**Owner:** Android-17
**Missions:** M7 (OpenClaw Frontier), M8 (Bench Testing)
**Created:** 2026-02-11

## Purpose

Real-time visibility into sub-agent swarms, GPU utilization, and task health. Know when things are working, catch failures fast.

---

## Core Metrics

### GPU Health
- **VRAM usage** (per GPU, % and absolute)
- **GPU utilization** (% compute)
- **Temperature** (if available via nvidia-smi)
- **Model loaded** (which model on which GPU)

### Agent/Session Health
- **Active sessions** (count)
- **Tokens/second** (throughput)
- **Queue depth** (pending requests)
- **Error rate** (failed completions)
- **Session age** (oldest active session)

### Task Metrics
- **Tasks completed** (last hour, last 24h)
- **Success rate** (%)
- **Average completion time**
- **Timeouts** (count)

---

## Data Sources

| Metric | Source | Endpoint |
|--------|--------|----------|
| GPU stats | nvidia-smi | Parse XML output |
| Cluster health | Smart proxy | `localhost:9199/status` |
| vLLM metrics | vLLM | `localhost:8000/metrics` (Prometheus format) |
| Session count | OpenClaw | TBD — may need gateway API |
| Error rate | vLLM tool proxy logs | Parse or add metrics endpoint |

---

## Tech Stack

**Philosophy:** No build step, no npm, no bundler. Pure simplicity.

- **Backend:** Python (FastAPI or Flask) — single file, <200 lines
- **Frontend:** Static HTML + htmx + Chart.js
- **Styling:** Pico CSS or similar classless framework
- **Refresh:** htmx polling every 5s, or SSE if feeling fancy
- **Deployment:** Single Docker container, optional Dream Server component

---

## UI Wireframe (ASCII)

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 Agent Dashboard                              [Auto-refresh] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ GPU 0 (.122)    │  │ GPU 1 (.143)    │  │ Cluster Health  │  │
│  │ ████████░░ 82%  │  │ ███████░░░ 71%  │  │ ✅ All nodes up │  │
│  │ Qwen-32B-AWQ    │  │ Qwen-32B        │  │ 2 GPUs active   │  │
│  │ 45°C            │  │ 42°C            │  │ Failover: Ready │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Throughput (tokens/sec)                    Last 15 minutes ││
│  │ ▁▂▃▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▅▆▇█▇▆▅▄▃▂▁                  ││
│  │ Peak: 142 t/s | Avg: 87 t/s | Current: 91 t/s              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌───────────────────────────┐  ┌─────────────────────────────┐ │
│  │ Active Sessions: 3        │  │ Task Stats (24h)            │ │
│  │ Oldest: 2m 34s            │  │ Completed: 847              │ │
│  │ Queue depth: 0            │  │ Success: 94.2%              │ │
│  │ Errors (1h): 2            │  │ Avg time: 3.2s              │ │
│  └───────────────────────────┘  └─────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Recent Errors                                              ││
│  │ 00:02:14 - Timeout on session abc123 (exceeded 30s)        ││
│  │ 23:47:02 - Parse error: invalid JSON in tool response      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Backend (This Sprint)
1. Create `/api/gpu` endpoint — parse nvidia-smi
2. Create `/api/cluster` endpoint — proxy 9199/status
3. Create `/api/vllm` endpoint — parse vLLM Prometheus metrics
4. Simple health aggregation

### Phase 2: Frontend (Next)
1. Static HTML shell
2. htmx fragments for each card
3. Chart.js for throughput graph
4. Auto-refresh with htmx polling

### Phase 3: Integration
1. Add to Dream Server docker-compose (optional service)
2. Document usage
3. Consider alerting (Discord webhook on error threshold)

---

## Open Questions

1. **Session data** — How do we get OpenClaw session counts? Gateway API? Parse logs?
2. **Historical data** — Do we persist metrics for graphs, or in-memory only?
3. **Multi-node** — Dashboard runs where? Central place that queries both nodes?

---

## Files to Create

```
dream-server/dashboard/
├── DESIGN.md          # This file
├── app.py             # FastAPI backend
├── templates/
│   └── index.html     # Main dashboard
├── static/
│   ├── style.css      # Minimal custom styles (if any)
│   └── dashboard.js   # Chart.js initialization
├── Dockerfile         # Optional containerization
└── README.md          # Usage docs
```

---

## Notes

- Start simple, iterate fast
- No auth for now (internal network only)
- Mobile-friendly would be nice but not required
