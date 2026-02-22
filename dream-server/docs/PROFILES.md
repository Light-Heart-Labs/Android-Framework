# Docker Compose Profiles

Dream Server uses Docker Compose profiles to let you choose which services to run. This saves resources when you don't need all features.

## Available Profiles

| Profile | Services | VRAM Required | Description |
|---------|----------|---------------|-------------|
| *(none)* | vLLM, Open WebUI, Dashboard | ~16GB | Chat only — minimal setup |
| `voice` | Whisper (STT), Kokoro (TTS) | +4GB | Speech recognition & synthesis |
| `livekit` | LiveKit, Voice Agent | +4GB | Real-time voice conversations |
| `workflows` | n8n | +2GB | Workflow automation |
| `rag` | Qdrant, Embeddings | +2GB | Document search & retrieval |
| `privacy` | Privacy Shield | +1GB | PII protection for API calls |
| `openclaw` | OpenClaw Gateway | +1GB | Agent management & messaging |
| `monitoring` | Prometheus, Grafana, **Token Spy** | +2GB | Metrics and dashboards |
| `full` | All services | ~32GB | Complete feature set |

**Note on Token Spy:** The `monitoring` and `full` profiles include Token Spy for LLM usage monitoring with TimescaleDB. Token Spy is a separate repo that must be checked out at `../products/token-spy` relative to the dream-server directory. If you don't have this repo, either remove the `monitoring` profile or clone the Token Spy repo first.

**Token Spy Quick Start:**
1. Set `TOKEN_SPY_DB_PASSWORD` in your `.env` file (generate with `openssl rand -base64 32`)
2. Start with monitoring: `docker-compose --profile monitoring up -d`
3. Point LLM clients to `http://localhost:8080` instead of `http://localhost:8000`
4. View usage data in the Token Spy dashboard at `http://localhost:3001`

See `docs/TOKEN-SPY-INTEGRATION.md` for detailed setup.

## Usage Examples

### Minimal Setup (Chat Only)
```bash
cd dream-server
docker-compose up -d
```
Services: vLLM, Open WebUI, Dashboard API/UI

### With Voice (STT + TTS)
```bash
docker-compose --profile voice up -d
```
Services: + Whisper (STT), Kokoro (TTS)

### Full Voice Agent
```bash
docker-compose --profile voice --profile livekit up -d
```
Services: + Voice pipeline with real-time conversation

### Complete Setup
```bash
docker-compose --profile voice --profile livekit --profile workflows --profile rag --profile privacy up -d
```
Services: Everything — chat, voice, workflows, document search, PII protection

### Development (All Services)
```bash
docker-compose --profile full up -d
```

## Checking What's Running

```bash
# See all services and their status
docker-compose ps

# See only running services
docker-compose ps --filter status=running

# Check resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## VRAM Savings

By using profiles, you can significantly reduce VRAM usage:

| Configuration | VRAM Used | Features |
|--------------|-----------|----------|
| Default (no profiles) | ~16GB | Chat, LLM inference |
| + voice | ~20GB | + Speech-to-text, Text-to-speech |
| + livekit | ~24GB | + Real-time voice agent |
| + full | ~32GB | + Workflows, RAG, Privacy Shield, Monitoring |

For 8GB VRAM systems, use the default profile only and rely on CPU for smaller models.

## Adding Profiles to Running System

You can add profiles without stopping existing services:

```bash
# Start with chat only
docker-compose up -d

# Later, add voice
docker-compose --profile voice up -d

# Later, add workflows
docker-compose --profile voice --profile workflows up -d
```

## Profile Dependencies

Some profiles depend on others:

- `livekit` profile requires `voice` profile (needs STT/TTS)
- `full` profile includes all services

## Troubleshooting

**Service not starting:**
Check if you enabled the right profile:
```bash
# This won't start voice services:
docker-compose up -d

# This will:
docker-compose --profile voice up -d
```

**"Service is required by" error:**
Some services depend on others. Make sure you include all required profiles.

**VRAM running out:**
Stop services you don't need:
```bash
docker-compose --profile voice stop
docker-compose up -d  # Keep only core services
```

## See Also

- `install.sh` — Automated setup with profile selection
- Dashboard "Features" page — Visual profile management
- `docs/INSTALL.md` — Detailed installation guide
