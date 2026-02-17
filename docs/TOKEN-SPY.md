# Token Spy — Setup & API Reference

Token Spy is a transparent API proxy that sits between your OpenClaw agents and upstream LLM providers. Every API call passes through Token Spy, which logs token usage, cost, latency, and session health — then forwards the request and response untouched.

Your agents don't need to change anything. Token Spy is invisible to the application layer.

---

## Architecture

```
Your agent -> Token Spy proxy (:9110) -> Upstream API (Anthropic, OpenAI, etc.)
                    |
                    v
                SQLite DB <- Dashboard (charts, tables, settings)
                    ^
                    |
             Session Manager (enforces limits on every request)
```

## Quick Setup

### Option 1: Via the Installer

Set `token_spy.enabled: true` in `config.yaml`, then run the installer:

```bash
./install.sh                  # Installs all enabled components
./install.sh --token-spy-only # Token Spy only
```

The installer copies Token Spy to `~/.openclaw/token-spy/`, generates the `.env`, installs dependencies, and creates a systemd service.

### Option 2: Standalone

```bash
cd token-spy
pip3 install -r requirements.txt
cp .env.example .env
# Edit .env — set AGENT_NAME and upstream URLs
AGENT_NAME=my-agent python3 -m uvicorn main:app --host 0.0.0.0 --port 9110
```

### Point Your Agent at Token Spy

In your `~/.openclaw/openclaw.json`, change each cloud provider's `baseUrl`:

**Anthropic:**
```json
"anthropic": {
    "baseUrl": "http://localhost:9110",
    "apiKey": "sk-ant-...",
    "api": "anthropic-messages"
}
```

**OpenAI-compatible (Moonshot, OpenAI, etc.):**
```json
"moonshot": {
    "baseUrl": "http://localhost:9110/v1",
    "apiKey": "sk-...",
    "api": "openai-completions"
}
```

Your API keys stay in OpenClaw's config — Token Spy just forwards them upstream.

### Open the Dashboard

Visit `http://localhost:9110/dashboard`. Data appears on the first API call.

---

## How Session Control Works

1. **Every API call**: Token Spy logs `conversation_history_chars` — the total size of all messages in the request payload.
2. **After logging**: Checks if history exceeds `session_char_limit`.
3. **If exceeded**: Deletes the largest active session file, forcing a fresh session.

This is smarter than file-size-based cleanup because it reads the actual request payload size — it knows exactly how much context the model is seeing.

### Why Characters Instead of Tokens?

One token is roughly 4 characters. Characters are used because:
- Available *before* sending to the API (tokens are counted by the provider *after*)
- Provider-agnostic — works the same for Anthropic, OpenAI, or local models
- The dashboard shows both: `51K / 100K (~25K tokens)`

---

## Multi-Agent Setup

Run one Token Spy instance per agent. They share the same database, so any dashboard shows all agents:

```bash
# Agent 1 — cloud model
AGENT_NAME=agent-1 python3 -m uvicorn main:app --host 0.0.0.0 --port 9110 &

# Agent 2 — cloud model
AGENT_NAME=agent-2 python3 -m uvicorn main:app --host 0.0.0.0 --port 9111 &

# Agent 3 — local model ($0 cost)
AGENT_NAME=agent-3 OPENAI_UPSTREAM=http://localhost:8000 API_PROVIDER=local \
  python3 -m uvicorn main:app --host 0.0.0.0 --port 9112 &
```

With systemd (templated service):
```bash
sudo systemctl enable --now token-spy@agent-1
sudo systemctl enable --now token-spy@agent-2
```

---

## Session Auto-Reset

Set `AGENT_SESSION_DIRS` to tell Token Spy where OpenClaw stores session files:

```bash
AGENT_SESSION_DIRS='{"agent-1":"~/.openclaw/agents/main/sessions"}'
```

When `conversation_history_chars` exceeds `session_char_limit` (default 200K chars / ~50K tokens), Token Spy deletes the largest `.jsonl` session file. The gateway creates a fresh session on the next turn.

Adjust limits per-agent via the dashboard Settings panel or the `/api/settings` endpoint.

---

## API Reference

### Settings

```bash
# Read
curl http://localhost:9110/api/settings

# Update global limit
curl -X POST http://localhost:9110/api/settings \
  -H "Content-Type: application/json" \
  -d '{"session_char_limit": 150000}'

# Per-agent override
curl -X POST http://localhost:9110/api/settings \
  -H "Content-Type: application/json" \
  -d '{"agents": {"my-agent": {"session_char_limit": 80000}}}'

# Clear override (inherit global)
curl -X POST http://localhost:9110/api/settings \
  -H "Content-Type: application/json" \
  -d '{"agents": {"my-agent": {"session_char_limit": null}}}'
```

### Monitoring

```bash
# Health check
curl http://localhost:9110/health

# Session status
curl http://localhost:9110/api/session-status?agent=my-agent

# Usage data (raw turns)
curl "http://localhost:9110/api/usage?hours=24&limit=100"

# Summary (aggregated by agent)
curl "http://localhost:9110/api/summary?hours=24"

# Manual session reset
curl -X POST "http://localhost:9110/api/reset-session?agent=my-agent"
```

### Session Health Levels

| Level | Meaning |
|-------|---------|
| `healthy` | History below limit |
| `monitor` | History exceeds limit (compaction expected) |
| `compact_soon` | History exceeds 2x limit |
| `reset_recommended` | History exceeds 2.5x limit (auto-reset fires at limit) |

### Dashboard

`http://localhost:9110/dashboard` — auto-refreshing UI with:
- Session health cards with live status badges
- Cost per turn timeline
- History growth chart with threshold lines
- Token usage breakdown (input, output, cache read, cache write)
- Cost breakdown doughnut (cache efficiency)
- Cumulative cost timeline
- Recent turns table
- Settings panel (edit limits and poll frequency)

---

## PostgreSQL (Optional)

SQLite works out of the box. For production with concurrent agents:

```bash
docker run -d --name token-spy-db \
  -e POSTGRES_USER=tokenspy \
  -e POSTGRES_PASSWORD=your-password \
  -e POSTGRES_DB=tokenspy \
  -p 5434:5432 \
  timescale/timescaledb:latest-pg15
```

In `.env`:
```
DB_BACKEND=postgres
DB_HOST=localhost
DB_PORT=5434
DB_NAME=tokenspy
DB_USER=tokenspy
DB_PASSWORD=your-password
```

---

## Using with Other Frameworks

Token Spy works with anything that supports a custom API base URL:

| Framework | How to Connect |
|-----------|----------------|
| **OpenClaw** | Change `baseUrl` in `openclaw.json` |
| **Claude Code** | `ANTHROPIC_BASE_URL=http://localhost:9110 claude` |
| **Python (anthropic SDK)** | `client = Anthropic(base_url="http://localhost:9110")` |
| **Python (openai SDK)** | `client = OpenAI(base_url="http://localhost:9110/v1")` |
| **curl** | `curl http://localhost:9110/v1/messages -H "x-api-key: ..." -d '{...}'` |

---

## Provider System

Token Spy uses a pluggable architecture for cost calculation:

```
token-spy/providers/
  base.py       — Abstract base class (LLMProvider)
  registry.py   — @register_provider decorator + lookup
  anthropic.py  — Claude models with cache-aware pricing
  openai.py     — OpenAI-compatible (GPT, Kimi, local models)
```

Add new providers by subclassing `LLMProvider` and decorating with `@register_provider("name")`.
