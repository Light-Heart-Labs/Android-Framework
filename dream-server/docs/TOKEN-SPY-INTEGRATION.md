# Token Spy Integration for Dream Server

Token Spy provides transparent LLM API monitoring — capturing token usage, costs, and session health metrics without requiring any code changes to your applications.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Open WebUI     │────▶│  Token Spy   │────▶│  vLLM           │
│  (Port 3000)    │     │  (Port 8080) │     │  (Port 8000)    │
└─────────────────┘     └──────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  TimescaleDB │
                        │  (Port 5433) │
                        └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  Dashboard   │
                        │  (Port 3001) │
                        └──────────────┘
```

## Quick Start

### 1. Prerequisites

Ensure Token Spy repo is cloned:
```bash
cd ..
git clone git@github.com:Lightheartdevs/token-spy.git products/token-spy
cd dream-server
```

### 2. Configure Environment

Add to your `.env` file:
```bash
# Token Spy Database Password (REQUIRED)
TOKEN_SPY_DB_PASSWORD=$(openssl rand -base64 32)

# Optional: Adjust ports if needed
TOKEN_SPY_PORT=8080
TOKEN_SPY_DB_PORT=5433
```

### 3. Start with Monitoring

```bash
docker-compose --profile monitoring up -d
```

### 4. Verify Installation

```bash
# Check all services are healthy
docker-compose --profile monitoring ps

# Test Token Spy proxy
curl http://localhost:8080/health

# View TimescaleDB connection
docker-compose logs token-spy-db | tail -20
```

## Usage

### Route LLM Traffic Through Token Spy

**Before (direct to vLLM):**
```python
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)
```

**After (through Token Spy):**
```python
client = OpenAI(
    base_url="http://localhost:8080/v1",  # Token Spy proxy
    api_key="not-needed"
)
```

### Open WebUI Configuration

Token Spy works transparently with Open WebUI:

1. Open WebUI automatically routes through Token Spy when using the `monitoring` profile
2. No configuration changes needed — the compose network handles routing
3. Usage data appears in both Open WebUI and Token Spy dashboards

### Manual Configuration

For external tools or custom integrations:

```bash
# Point any OpenAI-compatible client to Token Spy
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Dashboard Access

### Token Spy Dashboard
- **URL:** http://localhost:3001
- **Features:**
  - Real-time token usage
  - Cost tracking per session
  - Model performance metrics
  - Session replay

### Dream Server Dashboard
- **URL:** http://localhost:3001 (combined view)
- **Features:**
  - System health
  - GPU metrics
  - Token Spy integration panel

## Database Access

Connect directly to TimescaleDB for custom queries:

```bash
# Using psql (if installed locally)
psql postgresql://tokenspy:${TOKEN_SPY_DB_PASSWORD}@localhost:5433/tokenspy

# Using Docker
 docker-compose exec token-spy-db psql -U tokenspy -d tokenspy
```

### Common Queries

```sql
-- Total tokens by hour
SELECT 
  time_bucket('1 hour', timestamp) as hour,
  sum(prompt_tokens + completion_tokens) as total_tokens
FROM requests
GROUP BY hour
ORDER BY hour DESC;

-- Top sessions by cost
SELECT 
  session_id,
  sum(cost) as total_cost
FROM requests
GROUP BY session_id
ORDER BY total_cost DESC
LIMIT 10;

-- Error rate
SELECT 
  status_code,
  count(*) as count
FROM requests
GROUP BY status_code;
```

## Troubleshooting

### Token Spy Won't Start

```bash
# Check logs
docker-compose logs token-spy

# Common issues:
# 1. TOKEN_SPY_DB_PASSWORD not set
grep TOKEN_SPY_DB_PASSWORD .env

# 2. Token Spy repo not cloned
ls ../products/token-spy

# 3. Port conflicts
lsof -i :8080
lsof -i :5433
```

### Database Connection Issues

```bash
# Verify TimescaleDB is healthy
docker-compose ps token-spy-db

# Check database logs
docker-compose logs token-spy-db | grep -i error

# Reset database (WARNING: loses all data)
docker-compose down -v
docker-compose --profile monitoring up -d
```

### No Data in Dashboard

1. **Verify traffic is routing through Token Spy:**
   ```bash
   docker-compose logs token-spy | grep "request"
   ```

2. **Check database has data:**
   ```bash
   docker-compose exec token-spy-db psql -U tokenspy -d tokenspy -c "SELECT COUNT(*) FROM requests;"
   ```

3. **Verify upstream connection:**
   ```bash
   curl http://localhost:8080/v1/models
   ```

## Performance

### Resource Usage

| Component | CPU | Memory | Notes |
|-----------|-----|--------|-------|
| Token Spy | 0.1 cores | 256 MB | Per 100 req/sec |
| TimescaleDB | 0.5 cores | 1 GB | Grows with retention |
| Redis | 0.1 cores | 256 MB | Rate limiting cache |

### Scaling

For high-traffic deployments:

1. **Increase database resources:**
   ```yaml
   token-spy-db:
     deploy:
       resources:
         limits:
           memory: 4G
   ```

2. **Enable connection pooling:**
   ```bash
   TOKEN_SPY_MAX_CONNECTIONS=200
   ```

3. **Use external TimescaleDB:**
   ```bash
   TOKEN_SPY_DB_HOST=your-timescale-instance.cloud
   ```

## Security

- Token Spy runs as non-root user (`1000:1000`)
- Database password required (no default)
- No secrets logged to stdout
- PII can be scrubbed via Privacy Shield integration

## Migration from SQLite

If upgrading from the previous SQLite-based Token Spy:

1. **Backup existing data:**
   ```bash
   cp -r data/token-spy data/token-spy-backup
   ```

2. **Update .env with database password**

3. **Start with monitoring profile:**
   ```bash
   docker-compose --profile monitoring up -d
   ```

4. **Historical data will not be migrated** — TimescaleDB starts fresh

## See Also

- `docs/PROFILES.md` — Docker Compose profiles overview
- `../products/token-spy/README.md` — Token Spy standalone docs
- `../products/token-spy/API.md` — Token Spy API reference
