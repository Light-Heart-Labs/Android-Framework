# Token Spy

Transparent LLM API proxy that captures per-turn token usage, cost, latency, and session health. Sits between your application and upstream providers (Anthropic, OpenAI, Moonshot, local models), logging everything while forwarding requests and responses untouched -- including SSE streams.

## How It Works

```
Your agent -> Token Spy proxy -> Upstream API (Anthropic, OpenAI, etc.)
                  |
                  v
              SQLite DB <- Dashboard (charts, tables, settings)
                  ^
                  |
           Session Manager (polls every N minutes, enforces limits)
```

Point your agent's API base URL at Token Spy instead of the upstream provider. Token Spy forwards everything transparently -- your agent won't know it's there.

## Features

- **Real-time dashboard** -- session health cards, cost charts, token breakdown, cumulative cost, recent turns table
- **Session health monitoring** -- detects context bloat, recommends resets, can auto-kill sessions exceeding configurable character limits
- **Multi-provider** -- Anthropic Messages API (`/v1/messages`) and OpenAI Chat Completions (`/v1/chat/completions`)
- **Dual database backends** -- SQLite (zero-config default) and PostgreSQL/TimescaleDB for production
- **Per-agent settings** -- configurable session limits and poll intervals, editable via dashboard or REST API
- **Local model support** -- track self-hosted models (vLLM, Ollama) with $0 cost badges

## Standalone Usage

```bash
cd token-spy
pip install -r requirements.txt
cp .env.example .env
# Edit .env -- at minimum set AGENT_NAME
AGENT_NAME=my-agent python -m uvicorn main:app --host 0.0.0.0 --port 9110
```

Open `http://localhost:9110/dashboard` to see the monitoring UI.

## Configuration

See [.env.example](.env.example) for all available settings.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/dashboard` | GET | Web dashboard |
| `/api/settings` | GET/POST | Read/update settings |
| `/api/usage` | GET | Raw usage data |
| `/api/summary` | GET | Aggregated metrics by agent |
| `/api/session-status` | GET | Current session health |
| `/api/reset-session` | POST | Kill active session |
| `/token_events` | GET | SSE stream of token events |
| `/v1/messages` | POST | Anthropic proxy |
| `/v1/chat/completions` | POST | OpenAI-compatible proxy |

See [TOKEN-SPY-GUIDE.md](TOKEN-SPY-GUIDE.md) for full API documentation.

## Provider System

Pluggable cost calculation via provider classes:

```
providers/
  base.py       -- Abstract base class (LLMProvider)
  registry.py   -- @register_provider decorator + lookup
  anthropic.py  -- Claude models with cache-aware pricing
  openai.py     -- OpenAI-compatible (GPT, Kimi, local models)
```

Add new providers by subclassing `LLMProvider` and decorating with `@register_provider("name")`.
