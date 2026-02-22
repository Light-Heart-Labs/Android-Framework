# Agent Monitoring Dashboard

Real-time visibility into sub-agent swarms, GPU utilization, and task health.

## Features

- **GPU Monitoring**: VRAM usage, utilization %, temperature per GPU
- **Cluster Health**: Node status, failover readiness
- **Throughput Charts**: Real-time tokens/sec with Chart.js
- **Sub-Agent Status**: Active agents, tasks completed, uptime
- **Error Tracking**: Recent issues and failures

## Tech Stack

- **Backend**: Python FastAPI (single file, no build step)
- **Frontend**: Static HTML + htmx + Chart.js + Pico CSS
- **Refresh**: htmx polling every 5s, with toggle

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn httpx

# Run dashboard
cd dream-server/dashboard
python app.py

# Or with uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

Dashboard will be available at: http://localhost:8080

## API Endpoints

### JSON APIs
| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/gpu` | GPU metrics (nvidia-smi) |
| `GET /api/cluster` | Cluster status (from smart proxy) |
| `GET /api/vllm` | vLLM Prometheus metrics |
| `GET /api/agents` | Sub-agent status |
| `GET /api/metrics` | All metrics combined |
| `GET /api/history/gpu` | GPU utilization history |
| `GET /api/history/throughput` | Throughput history |

### HTMX Fragments
| Endpoint | Description |
|----------|-------------|
| `GET /api/fragments/gpu-cluster` | GPU cards + cluster health |
| `GET /api/fragments/sessions` | Active sessions |
| `GET /api/fragments/tasks` | Task statistics |
| `GET /api/fragments/agents` | Sub-agent table |
| `GET /api/fragments/errors` | Recent errors |

## Configuration

The dashboard expects these services to be available:

| Service | Default URL | Purpose |
|---------|-------------|---------|
| nvidia-smi | local binary | GPU metrics |
| Smart Proxy | localhost:9199/status | Cluster health |
| vLLM | localhost:8000/metrics | Inference metrics |

## Integration with Dream Server

Add to `docker-compose.yml`:

```yaml
services:
  dashboard:
    build: ./dashboard
    ports:
      - "8080:8080"
    environment:
      - VLLM_HOST=vllm
      - CLUSTER_STATUS_URL=http://smart-proxy:9199/status
    depends_on:
      - vllm
```

Or run standalone:

```bash
# From dream-server directory
cd dashboard
python app.py
```

## Files

```
dashboard/
├── app.py              # FastAPI backend
├── templates/
│   └── index.html      # Main dashboard (htmx + Chart.js)
├── static/             # Optional custom assets
├── DESIGN.md           # Design document
└── README.md           # This file
```

## Development

The dashboard is designed to be simple and hackable:

1. **No build step** - Edit HTML/JS directly
2. **Single Python file** - All backend logic in app.py
3. **CDN dependencies** - htmx, Chart.js, Pico CSS from CDN
4. **Hot reload** - Use `--reload` with uvicorn

## TODO

- [ ] Integrate with actual OpenClaw session API for agent data
- [ ] Parse vLLM/tool-proxy logs for error tracking
- [ ] Add Discord webhook for alerts
- [ ] Persist historical data (currently in-memory)
- [ ] Add mobile-responsive breakpoints
