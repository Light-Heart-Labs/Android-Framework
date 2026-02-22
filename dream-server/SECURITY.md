# Dream Server Security Guide

Security best practices for running Dream Server.

---

## ⚠️ Before You Start

1. **Run `./install.sh`** — generates secure random secrets automatically
2. **Never use default passwords** — if you see "changeme", change it
3. **Bind to localhost only** — exposed by default for a reason

---

## Secrets Management

### Generated Secrets

The installer auto-generates these in `.env`:

| Secret | Purpose |
|--------|---------|
| `WEBUI_SECRET` | Session signing for Open WebUI |
| `N8N_PASS` | Admin password for n8n |
| `LITELLM_KEY` | API key for LiteLLM gateway |

**Verify no defaults remain:**
```bash
grep -E "(PASSWORD|SECRET|KEY)" .env | grep -i changeme
```

### Manual Secret Rotation

```bash
# Generate new secrets
NEW_WEBUI=$(openssl rand -hex 32)
NEW_N8N=$(openssl rand -base64 16)
NEW_LITELLM="sk-dream-$(openssl rand -hex 16)"

# Update .env
sed -i "s/WEBUI_SECRET=.*/WEBUI_SECRET=$NEW_WEBUI/" .env
sed -i "s/N8N_PASS=.*/N8N_PASS=$NEW_N8N/" .env
sed -i "s/LITELLM_KEY=.*/LITELLM_KEY=$NEW_LITELLM/" .env

# Restart services
docker compose down && docker compose up -d
```

---

## Network Security

### Default: Localhost Only

All services bind to `127.0.0.1` — accessible only from the local machine.

### Exposing to LAN

For access from other devices on your network:

```bash
# Allow specific ports from local network
sudo ufw allow from 192.168.0.0/24 to any port 3000  # WebUI
sudo ufw allow from 192.168.0.0/24 to any port 8000  # LLM API
```

### Exposing to Internet (Not Recommended)

If you must expose publicly, use a reverse proxy with TLS:

**Caddy (simple):**
```bash
# /etc/caddy/Caddyfile
yourdomain.com {
    reverse_proxy localhost:3000
}
```

**nginx (with rate limiting):**
```nginx
limit_req_zone $binary_remote_addr zone=ai:10m rate=10r/m;

server {
    listen 443 ssl;
    server_name ai.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/ai.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.yourdomain.com/privkey.pem;
    
    auth_basic "AI Server";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        limit_req zone=ai burst=5;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Consider VPN** (Tailscale, WireGuard) instead of public exposure.

---

## Container Security

### Resource Limits

Prevent runaway containers:

```yaml
services:
  vllm:
    deploy:
      resources:
        limits:
          memory: 32G
        reservations:
          memory: 16G
```

### Principle of Least Privilege

The docker-compose.yml uses:
- Non-root users where possible
- Read-only volumes where appropriate
- GPU access only for services that need it

---

## Data Security

### What's Stored

| Directory | Contents | Sensitive? |
|-----------|----------|------------|
| `data/open-webui/` | Chat history, user accounts | **Yes** |
| `data/n8n/` | Workflows, credentials | **Yes** |
| `data/qdrant/` | Vector embeddings | Maybe |
| `data/whisper/` | Model cache | No |
| `models/` | Downloaded model weights | No |

### Encryption at Rest

Docker volumes aren't encrypted by default. For sensitive deployments:
- Use LUKS encrypted filesystem
- Or encrypted Docker volumes

### Backup Security

Backups contain sensitive data — encrypt them:

```bash
# Create encrypted backup
tar -cz data/ | gpg -c > dream-backup-$(date +%Y%m%d).tar.gz.gpg

# Restore
gpg -d dream-backup-YYYYMMDD.tar.gz.gpg | tar -xz
```

---

## API Security

### Recommended Architecture

```
Client → LiteLLM (with API key) → vLLM (localhost only)
```

vLLM has no authentication by default. Use LiteLLM as your authenticated gateway for remote access.

### Service-Specific

| Service | Auth | Notes |
|---------|------|-------|
| Open WebUI | Built-in | Change admin password, disable signups |
| n8n | Basic auth | Use strong password, enable 2FA |
| vLLM | None | Keep localhost-only, use LiteLLM for remote |
| LiteLLM | API key | Set `LITELLM_KEY` in .env |

---

## Monitoring

```bash
# Watch for errors
docker compose logs -f vllm | grep -i error

# Monitor resource usage
watch -n 5 'nvidia-smi; docker stats --no-stream'
```

Set up alerts for:
- High GPU/CPU usage (possible abuse)
- Failed auth attempts
- Unusual network traffic

---

## Updates

```bash
# Pull latest images
docker compose pull

# Recreate containers
docker compose up -d
```

Watch for security updates to: vLLM, Open WebUI, n8n, base images.

---

## Pre-Deployment Checklist

- [ ] Ran installer (secrets generated)
- [ ] No default passwords remain
- [ ] Firewall configured
- [ ] TLS enabled (if network-accessible)
- [ ] Rate limiting configured
- [ ] Backups scheduled
- [ ] Credentials documented securely

---

## Reporting Security Issues

Found a vulnerability?

1. **Do NOT open a public issue**
2. Email: security@lightheartlabs.com
3. Include: description, reproduction steps, potential impact

We'll respond within 48 hours.

---

*Security is a shared responsibility. When in doubt, keep it local.*
