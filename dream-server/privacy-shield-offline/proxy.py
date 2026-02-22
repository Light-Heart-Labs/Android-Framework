#!/usr/bin/env python3
"""
M3: API Privacy Shield - OFFLINE MODE
Zero-cloud PII proxy - only routes to local APIs
M1 Phase 2 - Blocks all external endpoints
"""

import os
import time
import httpx
import re
import hashlib
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
import uvicorn
import json
from cachetools import TTLCache

from pii_scrubber import PrivacyShield


app = FastAPI(title="API Privacy Shield - OFFLINE MODE", version="0.3.0-offline")

# Security: API Key Authentication
SHIELD_API_KEY = os.environ.get("SHIELD_API_KEY")
if not SHIELD_API_KEY:
    SHIELD_API_KEY = "not-needed"  # Default for offline/local-only mode

security_scheme = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """Verify API key for protected endpoints."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if credentials.credentials != SHIELD_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return credentials.credentials

# OFFLINE MODE: Only allow local endpoints
ALLOWED_TARGETS = [
    "http://vllm:8000",
    "http://vllm:8000/v1",
    "http://ollama:11434",
    "http://ollama:11434/v1",
    "http://localhost:8000",
    "http://localhost:11434",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:11434",
]

# Configuration from environment
DEFAULT_TARGET = os.getenv("TARGET_API_URL", "http://vllm:8000/v1")
TARGET_API_KEY = os.getenv("TARGET_API_KEY", "not-needed")
PORT = int(os.getenv("SHIELD_PORT", "8085"))
CACHE_ENABLED = os.getenv("PII_CACHE_ENABLED", "true").lower() == "true"
CACHE_SIZE = int(os.getenv("PII_CACHE_SIZE", "1000"))
BLOCK_EXTERNAL = os.getenv("BLOCK_EXTERNAL", "true").lower() == "true"

# OFFLINE MODE: Validate target is local-only
if BLOCK_EXTERNAL and DEFAULT_TARGET not in ALLOWED_TARGETS:
    # Check if it's at least a local-looking URL
    if not re.match(r'^https?://(localhost|127\.0\.0\.1|vllm|ollama|\[::1\]):?\d*', DEFAULT_TARGET):
        raise ValueError(f"OFFLINE MODE: Target API must be local. Got: {DEFAULT_TARGET}")

# Connection pool for better performance
http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=100, max_connections=200),
    timeout=httpx.Timeout(60.0, connect=5.0)
)

# Session store (TTLCache for bounded memory, auto-eviction of stale sessions)
sessions = TTLCache(maxsize=10000, ttl=3600)


class CachedPrivacyShield(PrivacyShield):
    """PrivacyShield with LRU cache for PII patterns."""
    
    def __init__(self, backend_client=None):
        super().__init__(backend_client)
        if CACHE_ENABLED:
            self._scrub_cached = lru_cache(maxsize=CACHE_SIZE)(self._scrub_impl)
    
    def _scrub_impl(self, text: str) -> str:
        """Internal scrub implementation."""
        return self.detector.scrub(text)
    
    def scrub(self, text: str) -> str:
        """Scrub with optional caching."""
        if CACHE_ENABLED and len(text) < 1000:  # Only cache small texts
            return self._scrub_cached(text)
        return self._scrub_impl(text)


def get_session(request: Request) -> CachedPrivacyShield:
    """Get or create session-specific PrivacyShield."""
    auth = request.headers.get("Authorization", "")
    # Use SHA256 for deterministic, stable session keying (hash() is not deterministic across restarts)
    if auth:
        session_key = hashlib.sha256(auth.encode()).hexdigest()
    else:
        client_info = str(request.client.host if request.client else "default")
        session_key = hashlib.sha256(client_info.encode()).hexdigest()
    
    if session_key not in sessions:
        sessions[session_key] = CachedPrivacyShield()
    
    return sessions[session_key]


def is_local_endpoint(url: str) -> bool:
    """OFFLINE MODE: Check if URL is a local-only endpoint."""
    if not BLOCK_EXTERNAL:
        return True
    
    # Check against allowed list
    if any(url.startswith(allowed) for allowed in ALLOWED_TARGETS):
        return True
    
    # Check for local patterns
    local_patterns = [
        r'^https?://localhost[:/]',
        r'^https?://127\.0\.0\.1[:/]',
        r'^https?://\[::1\][:/)]',
        r'^https?://vllm[:/]',
        r'^https?://ollama[:/]',
        r'^https?://whisper[:/]',
        r'^https?://kokoro[:/]',
        r'^https?://embeddings[:/]',
        r'^https?://192\.168\.',  # Local network (192.168.0.0/16)
        r'^https?://10\.\d+\.\d+\.\d+',  # Private subnet (10.0.0.0/8)
        r'^https?://172\.(1[6-9]|2[0-9]|3[01])\.',  # Private subnet (172.16.0.0/12)
    ]
    
    return any(re.match(pattern, url) for pattern in local_patterns)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "api-privacy-shield-offline",
        "version": "0.3.0-offline",
        "target_api": DEFAULT_TARGET,
        "cache_enabled": CACHE_ENABLED,
        "block_external": BLOCK_EXTERNAL,
        "active_sessions": len(sessions),
        "mode": "offline"
    }


@app.get("/stats")
async def stats():
    """Session statistics."""
    total_pii = sum(
        s.detector.get_stats()['unique_pii_count']
        for s in sessions.values()
    )
    return {
        "active_sessions": len(sessions),
        "total_pii_scrubbed": total_pii,
        "cache_enabled": CACHE_ENABLED,
        "cache_size": CACHE_SIZE,
        "block_external": BLOCK_EXTERNAL,
        "mode": "offline"
    }


@app.get("/config")
async def config():
    """OFFLINE MODE: Show allowed endpoints."""
    return {
        "mode": "offline",
        "target_api": DEFAULT_TARGET,
        "allowed_targets": ALLOWED_TARGETS if BLOCK_EXTERNAL else ["all (external allowed)"],
        "block_external": BLOCK_EXTERNAL,
        "cache_enabled": CACHE_ENABLED,
        "cache_size": CACHE_SIZE
    }


@app.post("/{path:path}", dependencies=[Depends(verify_api_key)])
@app.get("/{path:path}", dependencies=[Depends(verify_api_key)])
async def proxy(request: Request, path: str):
    """
    Proxy endpoint that scrubs PII from requests and restores in responses.
    OFFLINE MODE: Only allows local API endpoints.
    """
    start_time = time.time()
    shield = get_session(request)
    
    # Read and process request body
    body = await request.body()
    body_str = body.decode('utf-8') if body else ""
    
    # Scrub PII from request
    scrubbed_body, metadata = shield.process_request(body_str)
    
    # Determine target URL
    target_url = f"{DEFAULT_TARGET}/{path}"
    
    # OFFLINE MODE: Block external URLs
    if not is_local_endpoint(target_url):
        return JSONResponse(
            status_code=403,
            content={
                "error": "OFFLINE MODE: External API calls blocked",
                "shield": "active",
                "blocked_url": target_url,
                "allowed": "local endpoints only (vllm, ollama, localhost)"
            }
        )
    
    # Prepare headers
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ('host', 'content-length')}
    
    # Set host header for target
    host = DEFAULT_TARGET.split("//")[-1].split("/")[0]
    headers["host"] = host
    
    # Use target API key if configured
    if TARGET_API_KEY and TARGET_API_KEY != "not-needed":
        headers["Authorization"] = f"Bearer {TARGET_API_KEY}"
    
    try:
        if request.method == "POST":
            resp = await http_client.post(
                target_url,
                headers=headers,
                content=scrubbed_body.encode('utf-8')
            )
        else:
            resp = await http_client.get(
                target_url,
                headers=headers
            )
        
        # Read response
        response_body = resp.content.decode('utf-8')
        
        # Restore PII in response
        restored_body = shield.process_response(response_body)
        
        # Calculate overhead
        overhead_ms = (time.time() - start_time) * 1000
        
        # Add privacy headers
        response_headers = {
            "X-Privacy-Shield": "active-offline",
            "X-PII-Scrubbed": str(metadata.get('pii_count', 0)),
            "X-Processing-Time-Ms": f"{overhead_ms:.2f}",
            "Content-Type": resp.headers.get("Content-Type", "application/json")
        }
        
        return Response(
            content=restored_body,
            status_code=resp.status_code,
            headers=response_headers
        )
        
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"error": "Gateway timeout", "shield": "active-offline"}
        )
    except Exception as e:
        import re
        # Sanitize error message to prevent PII leakage in response
        error_str = str(e)
        error_str = re.sub(r'<PII_\w+_\w{12}>', '[REDACTED]', error_str)
        error_str = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', error_str)
        return JSONResponse(
            status_code=500,
            content={"error": "Request processing failed", "shield": "active-offline"}
        )


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    await http_client.aclose()


if __name__ == "__main__":
    print(f"🔒 API Privacy Shield (OFFLINE MODE) starting on port {PORT}")
    print(f"📡 Proxying to: {DEFAULT_TARGET}")
    print(f"🚫 External APIs: {'BLOCKED' if BLOCK_EXTERNAL else 'ALLOWED'}")
    print(f"💾 Cache: {'enabled' if CACHE_ENABLED else 'disabled'} (size={CACHE_SIZE})")
    print(f"🧪 Test with: curl http://localhost:{PORT}/health")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
