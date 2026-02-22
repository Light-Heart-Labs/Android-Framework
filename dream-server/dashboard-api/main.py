#!/usr/bin/env python3
"""
Dream Server Dashboard API
Lightweight backend providing system status for the Dashboard UI.

Endpoints:
  GET /health          - API health check
  GET /status          - Full system status (all metrics combined)
  GET /gpu             - GPU metrics (VRAM, utilization, temp)
  GET /services        - Docker service health
  GET /disk            - Disk usage for Dream Server paths
  GET /model           - Current model info
  GET /bootstrap       - Bootstrap download progress (if active)

Port: 3002 (Dashboard UI on 3001)
"""

import asyncio
import httpx
import json
import logging
import os
import subprocess
import aiohttp
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import shutil
import threading
from pydantic import BaseModel
import secrets

# Initialize module logger FIRST (before any logger usage)
logger = logging.getLogger(__name__)

# Security: API Key Authentication
# Generate a secure random key on startup if not provided
DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY")
if not DASHBOARD_API_KEY:
    # In production, this should fail hard. For bootstrap, generate a key and write to file.
    DASHBOARD_API_KEY = secrets.token_urlsafe(32)
    key_file = Path("/data/dashboard-api-key.txt")
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(DASHBOARD_API_KEY)
    key_file.chmod(0o600)
    logger.warning("DASHBOARD_API_KEY not set. Generated temporary key and wrote to %s (mode 0600). "
                   "Set DASHBOARD_API_KEY in your .env file for production.", key_file)

security_scheme = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """Verify API key for protected endpoints."""
    # Public health check endpoint doesn't require auth
    # All other endpoints require valid Bearer token
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    # B5 fix: Use timing-safe comparison to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, DASHBOARD_API_KEY):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key."
        )
    return credentials.credentials

# Import agent monitoring
from agent_monitor import (
    collect_metrics, get_full_agent_metrics,
    agent_metrics, cluster_status, token_usage, throughput
)

app = FastAPI(
    title="Dream Server Dashboard API",
    version="1.0.0",
    description="System status API for Dream Server Dashboard"
)

# CORS for Dashboard frontend
# Auto-detect LAN IPs and add them to allowed origins
def get_allowed_origins():
    """Get allowed CORS origins including auto-detected LAN IPs."""
    env_origins = os.environ.get("DASHBOARD_ALLOWED_ORIGINS", "")
    if env_origins:
        return env_origins.split(",")
    
    # Default localhost origins
    origins = [
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Auto-detect LAN IPs
    try:
        import socket
        hostname = socket.gethostname()
        local_ips = socket.gethostbyname_ex(hostname)[2]
        for ip in local_ips:
            if ip.startswith(("192.168.", "10.", "172.")):
                origins.append(f"http://{ip}:3001")
                origins.append(f"http://{ip}:3000")
    except Exception:
        pass
    
    return origins

ALLOWED_ORIGINS = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Config
INSTALL_DIR = os.environ.get("DREAM_INSTALL_DIR", os.path.expanduser("~/dream-server"))
DATA_DIR = os.environ.get("DREAM_DATA_DIR", os.path.expanduser("~/.dream-server"))

# Default host for services - use host.docker.internal when running in Docker
# Can be overridden with SERVICE_HOST env var
DEFAULT_SERVICE_HOST = os.environ.get("SERVICE_HOST", "host.docker.internal")

# Service definitions with health check endpoints
# Each service can override host via env var: VLLM_HOST, N8N_HOST, etc.
# Default uses host.docker.internal to reach host-bound services from container
SERVICES = {
    "vllm": {
        "host": os.environ.get("VLLM_HOST", "vllm"),
        "port": 8000,
        "health": "/v1/models",  # vLLM OpenAI API
        "name": "vLLM (LLM Inference)"
    },
    "open-webui": {
        "host": os.environ.get("WEBUI_HOST", "open-webui"),
        "port": int(os.environ.get("WEBUI_PORT", "8080")),  # Internal port
        "health": "/",
        "name": "Open WebUI (Chat)"
    },
    "n8n": {
        "host": os.environ.get("N8N_HOST", "n8n"),
        "port": 5678,
        "health": "/healthz",
        "name": "n8n (Workflows)"
    },
    "qdrant": {
        "host": os.environ.get("QDRANT_HOST", "qdrant"),
        "port": 6333,
        "health": "/",
        "name": "Qdrant (Vector DB)"
    },
    "whisper": {
        "host": os.environ.get("WHISPER_HOST", "whisper"),
        "port": 9000,
        "health": "/",
        "name": "Whisper (STT)"
    },
    "tts": {
        "host": os.environ.get("KOKORO_HOST", "tts"),
        "port": 8880,
        "health": "/",
        "name": "Kokoro (TTS)"
    },
    "livekit": {
        "host": os.environ.get("LIVEKIT_HOST", "livekit"),
        "port": 7880,
        "health": "/",
        "name": "LiveKit (Voice)"
    },
    "privacy-shield": {
        "host": os.environ.get("PRIVACY_SHIELD_HOST", "privacy-shield"),
        "port": int(os.environ.get("PRIVACY_SHIELD_PORT", "8085")),
        "health": "/health",
        "name": "Privacy Shield (PII Protection)"
    },
    "openclaw": {
        "host": os.environ.get("OPENCLAW_HOST", "openclaw"),
        "port": int(os.environ.get("OPENCLAW_PORT", "18789")),
        "health": "/",
        "name": "OpenClaw (Agents)"
    },
    "embeddings": {
        "host": os.environ.get("EMBEDDINGS_HOST", "embeddings"),
        "port": 80,
        "health": "/health",
        "name": "TEI (Embeddings)"
    },
    "voice-agent": {
        "host": os.environ.get("VOICE_AGENT_HOST", "livekit-voice-agent"),
        "port": 8181,
        "health": "/",
        "name": "Voice Agent"
    },
}


# --- Models ---

class GPUInfo(BaseModel):
    name: str
    memory_used_mb: int
    memory_total_mb: int
    memory_percent: float
    utilization_percent: int
    temperature_c: int
    
class ServiceStatus(BaseModel):
    id: str
    name: str
    port: int
    status: str  # "healthy", "unhealthy", "unknown"
    response_time_ms: Optional[float] = None
    
class DiskUsage(BaseModel):
    path: str
    used_gb: float
    total_gb: float
    percent: float
    
class ModelInfo(BaseModel):
    name: str
    size_gb: float
    context_length: int
    quantization: Optional[str] = None
    
class BootstrapStatus(BaseModel):
    active: bool
    model_name: Optional[str] = None
    percent: Optional[float] = None
    downloaded_gb: Optional[float] = None
    total_gb: Optional[float] = None
    speed_mbps: Optional[float] = None
    eta_seconds: Optional[int] = None

class FullStatus(BaseModel):
    timestamp: str
    gpu: Optional[GPUInfo] = None
    services: list[ServiceStatus]
    disk: DiskUsage
    model: Optional[ModelInfo] = None
    bootstrap: BootstrapStatus
    uptime_seconds: int


# --- Helper functions ---

def run_command(cmd: list[str], timeout: int = 5) -> tuple[bool, str]:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


async def get_vllm_metrics() -> dict:
    """Get vLLM Prometheus-style metrics."""
    try:
        vllm_metrics_url = os.getenv("VLLM_METRICS_URL", "http://vllm:8000/metrics")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(vllm_metrics_url)
            text = response.text
            metrics = {}
            for line in text.split("\n"):
                if "vllm:generation_tokens_per_second" in line and not line.startswith("#"):
                    try:
                        metrics["tokens_per_second_current"] = float(line.split()[-1])
                    except (ValueError, IndexError):
                        pass
            return metrics
    except Exception:
        return {}


def get_gpu_info() -> Optional[GPUInfo]:
    """Get GPU metrics from nvidia-smi."""
    success, output = run_command([
        "nvidia-smi",
        "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits"
    ])
    
    if not success or not output:
        return None
    
    try:
        parts = [p.strip() for p in output.split(",")]
        if len(parts) >= 5:
            mem_used = int(parts[1])
            mem_total = int(parts[2])
            return GPUInfo(
                name=parts[0],
                memory_used_mb=mem_used,
                memory_total_mb=mem_total,
                memory_percent=round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0,
                utilization_percent=int(parts[3]),
                temperature_c=int(parts[4])
            )
    except (ValueError, IndexError):
        pass
    
    return None


async def check_service_health(service_id: str, config: dict) -> ServiceStatus:
    """Check if a service is healthy by hitting its health endpoint."""
    
    host = config.get('host', 'localhost')
    url = f"http://{host}:{config['port']}{config['health']}"
    status = "unknown"
    response_time = None
    
    try:
        start = asyncio.get_event_loop().time()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get(url) as resp:
                response_time = (asyncio.get_event_loop().time() - start) * 1000
                status = "healthy" if resp.status < 500 else "unhealthy"
    except aiohttp.ClientConnectorError:
        status = "down"
    except Exception as e:
        logger.debug(f"Health check failed for {service_id} at {url}: {e}")
        status = "down"
    
    return ServiceStatus(
        id=service_id,
        name=config["name"],
        port=config["port"],
        status=status,
        response_time_ms=round(response_time, 1) if response_time else None
    )


def get_disk_usage() -> DiskUsage:
    """Get disk usage for the Dream Server install directory."""
    import shutil
    
    path = INSTALL_DIR if os.path.exists(INSTALL_DIR) else os.path.expanduser("~")
    total, used, free = shutil.disk_usage(path)
    
    return DiskUsage(
        path=path,
        used_gb=round(used / (1024**3), 2),
        total_gb=round(total / (1024**3), 2),
        percent=round(used / total * 100, 1)
    )


def get_model_info() -> Optional[ModelInfo]:
    """Get current model info from vLLM or config."""
    # Try reading from .env or config
    env_path = Path(INSTALL_DIR) / ".env"
    if env_path.exists():
        try:
            with open(env_path) as f:
                for line in f:
                    if line.startswith("VLLM_MODEL=") or line.startswith("LLM_MODEL="):
                        model_name = line.split("=", 1)[1].strip().strip('"\'')
                        # Parse model info from name
                        size_gb = 15.0  # Default estimate
                        context = 32768
                        quant = None
                        
                        name_lower = model_name.lower()
                        if "7b" in name_lower:
                            size_gb = 4.0
                        elif "14b" in name_lower:
                            size_gb = 8.0
                        elif "32b" in name_lower:
                            size_gb = 16.0
                        elif "70b" in name_lower:
                            size_gb = 35.0
                        
                        if "awq" in name_lower:
                            quant = "AWQ"
                        elif "gptq" in name_lower:
                            quant = "GPTQ"
                        elif "gguf" in name_lower:
                            quant = "GGUF"
                        
                        return ModelInfo(
                            name=model_name,
                            size_gb=size_gb,
                            context_length=context,
                            quantization=quant
                        )
        except Exception:
            pass
    
    return None


def get_bootstrap_status() -> BootstrapStatus:
    """Get bootstrap download progress if active."""
    status_file = Path(DATA_DIR) / "bootstrap-status.json"
    
    if not status_file.exists():
        return BootstrapStatus(active=False)
    
    try:
        with open(status_file) as f:
            data = json.load(f)
        
        status = data.get("status", "")
        # Only mark as inactive if status is explicitly "complete"
        # Empty status indicates unknown/initial state, keep active if other fields suggest progress
        if status == "complete":
            return BootstrapStatus(active=False)
        if status == "":
            # Empty status: check if we have actual progress data to determine activity
            if not data.get("bytesDownloaded") and not data.get("percent"):
                return BootstrapStatus(active=False)
            # Otherwise, treat as active bootstrap in unknown state
        
        # Parse ETA from string (e.g., "5m 30s" or "calculating...")
        eta_str = data.get("eta", "")
        eta_seconds = None
        if eta_str and eta_str.strip() and eta_str.strip() != "calculating...":
            try:
                # Simple parsing for "Xm Ys" format - strip parts to handle extra whitespace
                parts = [p.strip() for p in eta_str.replace("m", "").replace("s", "").split() if p.strip()]
                if len(parts) == 2:
                    eta_seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 1:
                    eta_seconds = int(parts[0])
            except (ValueError, IndexError):
                pass
        
        # Field names from model-bootstrap.sh: bytesDownloaded, bytesTotal, speedBytesPerSec
        bytes_downloaded = data.get("bytesDownloaded", 0)
        bytes_total = data.get("bytesTotal", 0)
        speed_bps = data.get("speedBytesPerSec", 0)
        
        # Parse percent safely (handle None, non-numeric, or missing)
        percent_raw = data.get("percent")
        percent = None
        if percent_raw is not None:
            try:
                percent = float(percent_raw)
            except (ValueError, TypeError):
                pass

        return BootstrapStatus(
            active=True,
            model_name=data.get("model"),
            percent=percent,
            downloaded_gb=bytes_downloaded / (1024**3) if bytes_downloaded else None,
            total_gb=bytes_total / (1024**3) if bytes_total else None,
            speed_mbps=speed_bps / (1024**2) if speed_bps else None,  # Convert B/s to MB/s
            eta_seconds=eta_seconds
        )
    except Exception:
        return BootstrapStatus(active=False)


def get_uptime() -> int:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime") as f:
            return int(float(f.read().split()[0]))
    except Exception:
        return 0


# --- Endpoints ---

@app.get("/health")
async def health():
    """API health check."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# --- Preflight Check Endpoints (for Setup Wizard) ---

class PortCheckRequest(BaseModel):
    ports: list[int]

class PortConflict(BaseModel):
    port: int
    service: str
    in_use: bool

@app.get("/api/preflight/docker", dependencies=[Depends(verify_api_key)])
async def preflight_docker():
    """Check if Docker is available and get version."""
    # If running inside a Docker container, Docker is available on the host
    if os.path.exists("/.dockerenv"):
        return {"available": True, "version": "available (host)"}
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse version string like "Docker version 24.0.7, build ..."
            version_str = result.stdout.strip()
            version = version_str.split()[2].rstrip(",") if len(version_str.split()) > 2 else "unknown"
            return {"available": True, "version": version}
        return {"available": False, "error": "Docker command failed"}
    except FileNotFoundError:
        return {"available": False, "error": "Docker not installed"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "Docker check timed out"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/api/preflight/gpu", dependencies=[Depends(verify_api_key)])
async def preflight_gpu():
    """Check if GPU is available and get basic info."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines and lines[0]:
                parts = [p.strip() for p in lines[0].split(",")]
                name = parts[0] if len(parts) > 0 else "Unknown"
                vram_mb = float(parts[1]) if len(parts) > 1 else 0
                vram_gb = round(vram_mb / 1024, 1)
                return {"available": True, "name": name, "vram": vram_gb}
        return {"available": False, "error": "nvidia-smi returned no data"}
    except FileNotFoundError:
        return {"available": False, "error": "nvidia-smi not found - NVIDIA drivers may not be installed"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "GPU check timed out"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.post("/api/preflight/ports", dependencies=[Depends(verify_api_key)])
async def preflight_ports(request: PortCheckRequest):
    """Check if required ports are available or already in use by expected services."""
    import socket
    
    # Map ports to expected services (for identifying conflicts vs expected usage)
    port_services = {
        3000: "Open WebUI",
        3001: "Dashboard",
        3002: "Dashboard API",
        5678: "n8n",
        6333: "Qdrant",
        8000: "vLLM",
        8880: "Kokoro (TTS)",
        9000: "Whisper (STT)",
        7880: "LiveKit",
    }
    
    conflicts = []
    
    for port in request.ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            # Try to bind to the port - if it fails, something is using it
            sock.bind(("0.0.0.0", port))
            sock.close()
        except socket.error:
            # Port is in use - this could be expected (our services) or a conflict
            conflicts.append({
                "port": port,
                "service": port_services.get(port, "Unknown"),
                "in_use": True
            })
    
    return {"conflicts": conflicts, "available": len(conflicts) == 0}


@app.get("/api/preflight/disk", dependencies=[Depends(verify_api_key)])
async def preflight_disk():
    """Check available disk space."""
    try:
        # Check data directory or home directory
        check_path = DATA_DIR if os.path.exists(DATA_DIR) else Path.home()
        usage = shutil.disk_usage(check_path)
        
        free_bytes = usage.free
        total_bytes = usage.total
        used_bytes = usage.used
        
        return {
            "free": free_bytes,
            "total": total_bytes,
            "used": used_bytes,
            "path": str(check_path)
        }
    except Exception as e:
        return {"error": str(e), "free": 0, "total": 0, "used": 0, "path": ""}


@app.get("/gpu", response_model=Optional[GPUInfo])
async def gpu(api_key: str = Depends(verify_api_key)):
    """Get GPU metrics."""
    info = get_gpu_info()
    if not info:
        raise HTTPException(status_code=503, detail="GPU not available or nvidia-smi failed")
    return info


async def _get_services():
    """Get all service health statuses (internal helper, no auth)."""
    tasks = [check_service_health(sid, cfg) for sid, cfg in SERVICES.items()]
    return await asyncio.gather(*tasks)


@app.get("/services", response_model=list[ServiceStatus])
async def services(api_key: str = Depends(verify_api_key)):
    """Get all service health statuses."""
    return await _get_services()


@app.get("/disk", response_model=DiskUsage)
async def disk(api_key: str = Depends(verify_api_key)):
    """Get disk usage."""
    return get_disk_usage()


@app.get("/model", response_model=Optional[ModelInfo])
async def model(api_key: str = Depends(verify_api_key)):
    """Get current model info."""
    return get_model_info()


@app.get("/bootstrap", response_model=BootstrapStatus)
async def bootstrap(api_key: str = Depends(verify_api_key)):
    """Get bootstrap download progress."""
    return get_bootstrap_status()


@app.get("/status", response_model=FullStatus)
async def status(api_key: str = Depends(verify_api_key)):
    """Get full system status (all metrics combined)."""
    # Run service checks in parallel (use internal helper to avoid auth recursion)
    service_statuses = await _get_services()

    return FullStatus(
        timestamp=datetime.now(timezone.utc).isoformat(),
        gpu=get_gpu_info(),
        services=service_statuses,
        disk=get_disk_usage(),
        model=get_model_info(),
        bootstrap=get_bootstrap_status(),
        uptime_seconds=get_uptime()
    )


@app.get("/api/status")
async def api_status(api_key: str = Depends(verify_api_key)):
    """
    Dashboard-compatible status endpoint.
    Schema matches Todd's Dashboard hooks exactly.
    """
    gpu_info = get_gpu_info()
    service_statuses = await _get_services()
    model_info = get_model_info()
    bootstrap_info = get_bootstrap_status()
    
    # Transform to Dashboard expected format
    # C1 fix: Convert MB to GB for frontend display (frontend expects GB, shows "X GB")
    gpu_data = None
    if gpu_info:
        gpu_data = {
            "name": gpu_info.name,
            "vramUsed": round(gpu_info.memory_used_mb / 1024, 1),  # Convert MB → GB
            "vramTotal": round(gpu_info.memory_total_mb / 1024, 1),  # Convert MB → GB
            "utilization": gpu_info.utilization_percent,
            "temperature": gpu_info.temperature_c
        }
    
    services_data = [
        {
            "name": s.name,
            "status": s.status,
            "port": s.port,
            "uptime": None  # Service-level uptime requires Docker API integration (future enhancement)
        }
        for s in service_statuses
    ]
    
    model_data = None
    if model_info:
        model_data = {
            "name": model_info.name,
            "tokensPerSecond": None,  # Real-time throughput via vLLM metrics endpoint
            "contextLength": model_info.context_length
        }
    
    bootstrap_data = None
    if bootstrap_info.active:
        bootstrap_data = {
            "active": True,
            "model": bootstrap_info.model_name or "Full Model",
            "percent": bootstrap_info.percent or 0,
            "bytesDownloaded": int((bootstrap_info.downloaded_gb or 0) * 1024**3),
            "bytesTotal": int((bootstrap_info.total_gb or 0) * 1024**3),
            "eta": bootstrap_info.eta_seconds,
            "speedMbps": bootstrap_info.speed_mbps
        }
    
    # Determine tier from VRAM
    tier = "Unknown"
    if gpu_info:
        vram_gb = gpu_info.memory_total_mb / 1024
        if vram_gb >= 80:
            tier = "Professional"
        elif vram_gb >= 24:
            tier = "Prosumer"
        elif vram_gb >= 16:
            tier = "Standard"
        elif vram_gb >= 8:
            tier = "Entry"
        else:
            tier = "Minimal"
    
    return {
        "gpu": gpu_data,
        "services": services_data,
        "model": model_data,
        "bootstrap": bootstrap_data,
        "uptime": get_uptime(),
        "version": app.version,  # Dynamic version from app configuration
        "tier": tier
    }


# --- Model Catalog ---

# Curated model catalog with hardware requirements
MODEL_CATALOG = [
    {
        "id": "Qwen/Qwen2.5-1.5B-Instruct",
        "name": "Qwen2.5 1.5B",
        "size_gb": 1.2,
        "vram_required_gb": 2,
        "context_length": 32768,
        "specialty": "Bootstrap",
        "description": "Ultra-fast bootstrap model for instant startup",
        "tokens_per_sec_estimate": 200,
        "quantization": None
    },
    {
        "id": "Qwen/Qwen2.5-7B-Instruct",
        "name": "Qwen2.5 7B",
        "size_gb": 4.2,
        "vram_required_gb": 6,
        "context_length": 32768,
        "specialty": "Fast",
        "description": "Fast general-purpose model, good for simple tasks",
        "tokens_per_sec_estimate": 120,
        "quantization": None
    },
    {
        "id": "Qwen/Qwen2.5-14B-Instruct-AWQ",
        "name": "Qwen2.5 14B AWQ",
        "size_gb": 8.1,
        "vram_required_gb": 10,
        "context_length": 32768,
        "specialty": "Balanced",
        "description": "Balanced performance and quality",
        "tokens_per_sec_estimate": 75,
        "quantization": "AWQ"
    },
    {
        "id": "Qwen/Qwen2.5-32B-Instruct-AWQ",
        "name": "Qwen2.5 32B AWQ",
        "size_gb": 15.7,
        "vram_required_gb": 14,
        "context_length": 32768,
        "specialty": "General",
        "description": "High-quality general purpose, recommended for most users",
        "tokens_per_sec_estimate": 54,
        "quantization": "AWQ"
    },
    {
        "id": "Qwen/Qwen2.5-72B-Instruct-AWQ",
        "name": "Qwen2.5 72B AWQ",
        "size_gb": 35.0,
        "vram_required_gb": 42,
        "context_length": 32768,
        "specialty": "Quality",
        "description": "Maximum quality, requires high-end GPU",
        "tokens_per_sec_estimate": 28,
        "quantization": "AWQ"
    },
    {
        "id": "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
        "name": "Qwen2.5 Coder 32B AWQ",
        "size_gb": 15.7,
        "vram_required_gb": 14,
        "context_length": 32768,
        "specialty": "Code",
        "description": "Optimized for coding tasks and technical work",
        "tokens_per_sec_estimate": 54,
        "quantization": "AWQ"
    },
    {
        "id": "mistralai/Codestral-22B-v0.1",
        "name": "Codestral 22B",
        "size_gb": 12.3,
        "vram_required_gb": 12,
        "context_length": 32768,
        "specialty": "Code",
        "description": "Mistral's coding specialist",
        "tokens_per_sec_estimate": 65,
        "quantization": None
    },
    {
        "id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        "name": "DeepSeek R1 32B",
        "size_gb": 16.0,
        "vram_required_gb": 15,
        "context_length": 32768,
        "specialty": "Reasoning",
        "description": "Advanced reasoning capabilities",
        "tokens_per_sec_estimate": 45,
        "quantization": None
    }
]


def get_downloaded_models() -> list[str]:
    """Get list of models already downloaded to local storage."""
    models_dir = Path(INSTALL_DIR) / "models"
    downloaded = []
    
    if models_dir.exists():
        # Check for HuggingFace cache structure
        for item in models_dir.iterdir():
            if item.is_dir():
                # Check for model config file
                if (item / "config.json").exists():
                    downloaded.append(item.name)
                # Check HF cache structure (models--org--name)
                elif item.name.startswith("models--"):
                    parts = item.name.replace("models--", "").split("--")
                    if len(parts) >= 2:
                        downloaded.append(f"{parts[0]}/{parts[1]}")
    
    return downloaded


def get_current_loaded_model() -> Optional[str]:
    """Get the currently loaded model from vLLM."""
    # Try reading from .env
    env_path = Path(INSTALL_DIR) / ".env"
    if env_path.exists():
        try:
            with open(env_path) as f:
                for line in f:
                    if line.startswith("VLLM_MODEL=") or line.startswith("LLM_MODEL="):
                        return line.split("=", 1)[1].strip().strip('"\'')
        except Exception:
            pass
    return None


@app.get("/api/models")
async def api_models(api_key: str = Depends(verify_api_key)):
    """
    Get model catalog with download/load status.
    Dashboard-compatible format.
    """
    gpu_info = get_gpu_info()
    gpu_vram_gb = (gpu_info.memory_total_mb / 1024) if gpu_info else 0
    gpu_vram_used_gb = (gpu_info.memory_used_mb / 1024) if gpu_info else 0
    gpu_vram_free_gb = gpu_vram_gb - gpu_vram_used_gb
    
    downloaded = get_downloaded_models()
    current_model = get_current_loaded_model()
    
    models = []
    for model in MODEL_CATALOG:
        # Determine status
        model_id = model["id"]
        is_downloaded = any(model_id in d or d in model_id for d in downloaded)
        is_loaded = current_model and (model_id in current_model or current_model in model_id)
        
        if is_loaded:
            status = "loaded"
        elif is_downloaded:
            status = "downloaded"
        else:
            status = "available"
        
        # Check if it fits in VRAM
        fits_vram = model["vram_required_gb"] <= gpu_vram_gb
        fits_free_vram = model["vram_required_gb"] <= gpu_vram_free_gb
        
        models.append({
            "id": model["id"],
            "name": model["name"],
            "size": f"{model['size_gb']} GB",
            "sizeGb": model["size_gb"],
            "vramRequired": model["vram_required_gb"],
            "contextLength": model["context_length"],
            "specialty": model["specialty"],
            "description": model["description"],
            "tokensPerSec": model["tokens_per_sec_estimate"],
            "quantization": model["quantization"],
            "status": status,
            "fitsVram": fits_vram,
            "fitsCurrentVram": fits_free_vram
        })
    
    return {
        "models": models,
        "gpu": {
            "vramTotal": gpu_vram_gb,
            "vramUsed": gpu_vram_used_gb,
            "vramFree": gpu_vram_free_gb
        },
        "currentModel": current_model
    }


@app.post("/api/models/{model_id:path}/download")
async def download_model(model_id: str, api_key: str = Depends(verify_api_key)):
    """Start downloading a model in the background."""
    
    # Check if model exists in catalog
    model_info = next((m for m in MODEL_CATALOG if m["id"] == model_id), None)
    if not model_info:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    # Check if already downloading
    status_file = Path(DATA_DIR) / "model-download-status.json"
    if status_file.exists():
        try:
            with open(status_file) as f:
                current = json.load(f)
            if current.get("status") == "downloading":
                raise HTTPException(status_code=409, detail="Another download is in progress")
        except Exception:
            pass
    
    # Write initial status
    download_status = {
        "status": "downloading",
        "model": model_id,
        "percent": 0,
        "bytesDownloaded": 0,
        "bytesTotal": int(model_info["size_gb"] * 1024**3),
        "speedBytesPerSec": 0,
        "eta": "calculating...",
        "startedAt": datetime.now(timezone.utc).isoformat()
    }
    
    with open(status_file, "w") as f:
        json.dump(download_status, f)
    
    # Start background download
    def do_download():
        import subprocess
        script_path = Path(INSTALL_DIR) / "scripts" / "model-bootstrap.sh"
        if script_path.exists():
            env = os.environ.copy()
            env["FULL_MODEL"] = model_id
            subprocess.run(
                [str(script_path), "--background"],
                env=env,
                cwd=str(INSTALL_DIR)
            )
    
    # Run in background thread
    import threading
    thread = threading.Thread(target=do_download, daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "model": model_id,
        "message": f"Download started for {model_info['name']}. Check /api/models/download-status for progress."
    }


@app.get("/api/models/download-status")
async def get_download_status(api_key: str = Depends(verify_api_key)):
    """Get current model download progress."""
    status_file = Path(DATA_DIR) / "model-download-status.json"
    
    if not status_file.exists():
        return {"status": "idle", "message": "No download in progress"}
    
    try:
        with open(status_file) as f:
            return json.load(f)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/models/{model_id:path}/load")
async def load_model(model_id: str, api_key: str = Depends(verify_api_key)):
    """Load a downloaded model into vLLM."""
    # Check if model is downloaded
    downloaded = get_downloaded_models()
    if not any(model_id in d or d in model_id for d in downloaded):
        raise HTTPException(status_code=400, detail="Model not downloaded yet")
    
    # Run upgrade-model.sh
    script_path = Path(INSTALL_DIR) / "scripts" / "upgrade-model.sh"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="upgrade-model.sh not found")
    
    def do_load():
        import subprocess
        subprocess.run(
            [str(script_path), model_id],
            cwd=str(INSTALL_DIR)
        )
    
    import threading
    thread = threading.Thread(target=do_load, daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "model": model_id,
        "message": "Model loading started. vLLM will restart. This may take a minute."
    }


@app.delete("/api/models/{model_id:path}")
async def delete_model(model_id: str, api_key: str = Depends(verify_api_key)):
    """Delete a downloaded model."""
    models_dir = Path(INSTALL_DIR) / "models"
    
    # Find the model directory
    target_dir = None
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.is_dir():
                if model_id in item.name or item.name in model_id:
                    target_dir = item
                    break
                # Check HF cache structure
                if item.name.startswith("models--"):
                    hf_id = item.name.replace("models--", "").replace("--", "/")
                    if model_id in hf_id or hf_id in model_id:
                        target_dir = item
                        break
    
    if not target_dir:
        raise HTTPException(status_code=404, detail="Model not found in local storage")
    
    # Check it's not the currently loaded model
    current = get_current_loaded_model()
    if current and (model_id in current or current in model_id):
        raise HTTPException(status_code=400, detail="Cannot delete currently loaded model")
    
    # Delete the directory
    import shutil
    try:
        shutil.rmtree(target_dir)
        return {
            "status": "deleted",
            "model": model_id,
            "message": f"Deleted {target_dir.name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")


# --- Voice API ---

class VoiceTokenRequest(BaseModel):
    identity: str
    room: str = "dream-voice"

@app.post("/api/voice/token")
async def voice_token(request: VoiceTokenRequest, api_key: str = Depends(verify_api_key)):
    """
    Generate a LiveKit access token for voice chat.
    The dashboard uses this to connect to the voice agent.
    """
    try:
        from livekit import api
        
        # Read LiveKit credentials from environment (no defaults for security)
        api_key = os.environ.get("LIVEKIT_API_KEY")
        api_secret = os.environ.get("LIVEKIT_API_SECRET")
        if not api_key or not api_secret:
            raise HTTPException(
                status_code=500,
                detail="LIVEKIT_API_KEY and LIVEKIT_API_SECRET environment variables must be set"
            )
        
        # Create token with voice permissions
        token = api.AccessToken(api_key, api_secret)
        token.with_identity(request.identity)
        token.with_name(f"Dashboard User {request.identity[-6:]}")
        
        # Grant permissions for the voice room
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=request.room,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        ))
        
        # Token valid for 24 hours
        token.with_ttl(timedelta(hours=24))
        
        # Create agent dispatch for this room
        try:
            livekit_url = os.environ.get("LIVEKIT_URL", "http://localhost:7880").replace("ws://", "http://").replace("wss://", "https://")
            lk_api = api.LiveKitAPI(
                url=livekit_url,
                api_key=api_key,
                api_secret=api_secret
            )
            # Dispatch agent to the room
            await lk_api.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    room=request.room,
                    agent_name=""  # Empty string dispatches any available agent
                )
            )
            logger.info(f"Agent dispatched to room {request.room}")
        except Exception as dispatch_error:
            logger.warning(f"Agent dispatch failed (agent may already be in room): {dispatch_error}")
        
        return {
            "token": token.to_jwt(),
            "room": request.room,
            "livekitUrl": os.environ.get("LIVEKIT_URL", "ws://localhost:7880")
        }
        
    except ImportError:
        # LiveKit SDK not installed - return placeholder for development
        return {
            "error": "LiveKit SDK not available",
            "token": None,
            "room": request.room,
            "message": "Voice features require livekit-api package. Install with: pip install livekit-api"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")


@app.get("/api/voice/status")
async def voice_status(api_key: str = Depends(verify_api_key)):
    """Check if voice services are available."""
    
    # Service URLs (configurable via env vars, with Docker service name defaults)
    # naming matches the SDK's base_url parameter for clarity
    stt_base_url = os.environ.get("STT_BASE_URL", "http://whisper:9000")
    kokoro_url = os.environ.get("KOKORO_URL", "http://tts:8880")
    livekit_host = os.environ.get("LIVEKIT_HOST", "livekit")
    
    async def check_service(url: str, health_path: str = "/") -> str:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"{url}{health_path}") as resp:
                    return "healthy" if resp.status < 500 else "unhealthy"
        except Exception:
            return "unhealthy"
    
    # Check all services concurrently
    stt_status, tts_status, livekit_status = await asyncio.gather(
        check_service(stt_base_url, "/"),
        check_service(kokoro_url, "/health"),
        check_service(f"http://{livekit_host}:7880", "/")
    )
    
    all_healthy = all(s == "healthy" for s in [stt_status, tts_status, livekit_status])
    
    return {
        "available": all_healthy,
        "services": {
            "stt": {"name": "Whisper (STT)", "status": stt_status, "port": 9000},
            "tts": {"name": "Kokoro (TTS)", "status": tts_status, "port": 8880},
            "livekit": {"name": "LiveKit", "status": livekit_status, "port": 7880}
        },
        "message": "Voice ready" if all_healthy else "Some voice services unavailable"
    }


# --- Workflow API ---

WORKFLOW_DIR = Path(INSTALL_DIR) / "workflows"
WORKFLOW_CATALOG_FILE = WORKFLOW_DIR / "catalog.json"

# n8n API base URL
N8N_URL = os.environ.get("N8N_URL", "http://n8n:5678")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")  # Optional API key

# Warn if N8N_API_KEY is empty but N8N_URL is custom (user may need to set API key)
if N8N_URL != "http://n8n:5678" and not N8N_API_KEY:
    logger.warning("N8N_URL is set but N8N_API_KEY is empty - n8n requests may fail")


def load_workflow_catalog() -> dict:
    """Load workflow catalog from JSON file."""
    if not WORKFLOW_CATALOG_FILE.exists():
        return {"workflows": [], "categories": {}}
    try:
        with open(WORKFLOW_CATALOG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"workflows": [], "categories": {}}


async def get_n8n_workflows() -> list[dict]:
    """Get all workflows from n8n API."""
    try:
        headers = {}
        if N8N_API_KEY:
            headers["X-N8N-API-KEY"] = N8N_API_KEY
        else:
            logger.debug("No N8N_API_KEY set, attempting unauthenticated request")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{N8N_URL}/api/v1/workflows", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(f"Fetched {len(data.get('data', []))} workflows from n8n")
                    return data.get("data", [])
                else:
                    logger.warning(f"n8n API returned status {resp.status} for workflows endpoint")
    except Exception as e:
        logger.warning(f"Failed to fetch workflows from n8n: {e}")
    return []


async def check_workflow_dependencies(deps: list[str]) -> dict[str, bool]:
    """Check if required services are running."""
    service_map = {
        "vllm": {"port": 8000, "health": "/health", "name": "vLLM"},
        "qdrant": {"port": 6333, "health": "/", "name": "Qdrant"},
        "whisper": {"port": 9000, "health": "/", "name": "Whisper"},  # Fixed: was 9001
        "tts": {"port": 8880, "health": "/", "name": "Kokoro"},
        "n8n": {"port": 5678, "health": "/healthz", "name": "n8n"},
    }
    
    results = {}
    for dep in deps:
        if dep in service_map:
            status = await check_service_health(dep, service_map[dep])
            results[dep] = status.status == "healthy"
        else:
            results[dep] = True  # Unknown deps assumed OK
    
    return results


@app.get("/api/workflows")
async def api_workflows(api_key: str = Depends(verify_api_key)):
    """
    Get workflow catalog with status and dependency info.
    """
    catalog = load_workflow_catalog()
    n8n_workflows = await get_n8n_workflows()
    
    # Map n8n workflows by name for quick lookup
    n8n_by_name = {w.get("name", "").lower(): w for w in n8n_workflows}
    
    workflows = []
    for wf in catalog.get("workflows", []):
        # Check if workflow is installed in n8n
        wf_name_lower = wf["name"].lower()
        installed = None
        for n8n_name, n8n_wf in n8n_by_name.items():
            if wf_name_lower in n8n_name or n8n_name in wf_name_lower:
                installed = n8n_wf
                break
        
        # Check dependencies
        dep_status = await check_workflow_dependencies(wf.get("dependencies", []))
        all_deps_met = all(dep_status.values())
        
        # Get execution count if installed
        executions = 0
        if installed:
            executions = installed.get("statistics", {}).get("executions", {}).get("total", 0)
        
        workflows.append({
            "id": wf["id"],
            "name": wf["name"],
            "description": wf["description"],
            "icon": wf.get("icon", "Workflow"),
            "category": wf.get("category", "general"),
            "status": "active" if installed and installed.get("active") else ("installed" if installed else "available"),
            "installed": installed is not None,
            "active": installed.get("active", False) if installed else False,
            "n8nId": installed.get("id") if installed else None,
            "dependencies": wf.get("dependencies", []),
            "dependencyStatus": dep_status,
            "allDependenciesMet": all_deps_met,
            "diagram": wf.get("diagram", {}),
            "setupTime": wf.get("setupTime", "~2 min"),
            "executions": executions,
            "featured": wf.get("featured", False)
        })
    
    return {
        "workflows": workflows,
        "categories": catalog.get("categories", {}),
        "n8nUrl": N8N_URL,
        "n8nAvailable": len(n8n_workflows) > 0 or await check_n8n_available()
    }


async def check_n8n_available() -> bool:
    """Check if n8n is responding."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get(f"{N8N_URL}/healthz") as resp:
                status = resp.status < 500
                logger.debug(f"n8n health check ({N8N_URL}/healthz): {'ok' if status else 'failed'}")
                return status
    except Exception as e:
        logger.debug(f"n8n health check failed: {e}")
        return False


@app.post("/api/workflows/{workflow_id}/enable")
async def enable_workflow(workflow_id: str, api_key: str = Depends(verify_api_key)):
    """
    Import a workflow template into n8n.
    """
    # Validate workflow_id format (alphanumeric, underscore, hyphen only)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', workflow_id):
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")
    
    catalog = load_workflow_catalog()
    
    # Find workflow in catalog
    wf_info = None
    for wf in catalog.get("workflows", []):
        if wf["id"] == workflow_id:
            wf_info = wf
            break
    
    if not wf_info:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
    
    # Check dependencies
    dep_status = await check_workflow_dependencies(wf_info.get("dependencies", []))
    missing_deps = [dep for dep, ok in dep_status.items() if not ok]
    
    if missing_deps:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing dependencies: {', '.join(missing_deps)}. Enable these services first."
        )
    
    # Load workflow JSON (safe path join using pathlib)
    workflow_file = WORKFLOW_DIR / wf_info["file"]
    # Ensure the resolved path is still under WORKFLOW_DIR (prevent path traversal)
    try:
        workflow_file = workflow_file.resolve()
        if not str(workflow_file).startswith(str(WORKFLOW_DIR.resolve())):
            raise HTTPException(status_code=400, detail="Invalid workflow file path")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workflow file path")
    
    if not workflow_file.exists():
        raise HTTPException(status_code=404, detail=f"Workflow file not found: {wf_info['file']}")
    
    try:
        with open(workflow_file) as f:
            workflow_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read workflow: {e}")
    
    # Import to n8n
    try:
        headers = {"Content-Type": "application/json"}
        if N8N_API_KEY:
            headers["X-N8N-API-KEY"] = N8N_API_KEY
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # Create workflow
            async with session.post(
                f"{N8N_URL}/api/v1/workflows",
                headers=headers,
                json=workflow_data
            ) as resp:
                if resp.status == 200 or resp.status == 201:
                    result = await resp.json()
                    n8n_id = result.get("data", {}).get("id")
                    
                    # Activate the workflow
                    if n8n_id:
                        async with session.patch(
                            f"{N8N_URL}/api/v1/workflows/{n8n_id}",
                            headers=headers,
                            json={"active": True}
                        ) as activate_resp:
                            activated = activate_resp.status == 200
                    else:
                        activated = False
                    
                    return {
                        "status": "success",
                        "workflowId": workflow_id,
                        "n8nId": n8n_id,
                        "activated": activated,
                        "message": f"{wf_info['name']} is now active!"
                    }
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"n8n API error: {error_text}")
                    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach n8n: {e}")


@app.delete("/api/workflows/{workflow_id}")
async def disable_workflow(workflow_id: str, api_key: str = Depends(verify_api_key)):
    """
    Remove a workflow from n8n.
    """
    # Get current n8n workflows
    n8n_workflows = await get_n8n_workflows()
    
    # Find the workflow
    catalog = load_workflow_catalog()
    wf_info = next((wf for wf in catalog.get("workflows", []) if wf["id"] == workflow_id), None)
    
    if not wf_info:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
    
    # Find in n8n
    n8n_wf = None
    wf_name_lower = wf_info["name"].lower()
    for wf in n8n_workflows:
        if wf_name_lower in wf.get("name", "").lower():
            n8n_wf = wf
            break
    
    if not n8n_wf:
        raise HTTPException(status_code=404, detail="Workflow not installed in n8n")
    
    # Delete from n8n
    try:
        headers = {}
        if N8N_API_KEY:
            headers["X-N8N-API-KEY"] = N8N_API_KEY
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.delete(
                f"{N8N_URL}/api/v1/workflows/{n8n_wf['id']}",
                headers=headers
            ) as resp:
                if resp.status == 200 or resp.status == 204:
                    return {
                        "status": "success",
                        "workflowId": workflow_id,
                        "message": f"{wf_info['name']} has been removed"
                    }
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"n8n API error: {error_text}")
                    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach n8n: {e}")


@app.get("/api/workflows/{workflow_id}/executions")
async def workflow_executions(workflow_id: str, limit: int = 20, api_key: str = Depends(verify_api_key)):
    """
    Get recent executions for a workflow.
    """
    # Get current n8n workflows
    n8n_workflows = await get_n8n_workflows()
    
    # Find the workflow
    catalog = load_workflow_catalog()
    wf_info = next((wf for wf in catalog.get("workflows", []) if wf["id"] == workflow_id), None)
    
    if not wf_info:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
    
    # Find in n8n
    n8n_wf = None
    wf_name_lower = wf_info["name"].lower()
    for wf in n8n_workflows:
        if wf_name_lower in wf.get("name", "").lower():
            n8n_wf = wf
            break
    
    if not n8n_wf:
        return {"executions": [], "message": "Workflow not installed"}
    
    # Get executions from n8n
    try:
        headers = {}
        if N8N_API_KEY:
            headers["X-N8N-API-KEY"] = N8N_API_KEY
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(
                f"{N8N_URL}/api/v1/executions",
                headers=headers,
                params={"workflowId": n8n_wf["id"], "limit": limit}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "workflowId": workflow_id,
                        "n8nId": n8n_wf["id"],
                        "executions": data.get("data", [])
                    }
                else:
                    return {"executions": [], "error": "Failed to fetch executions"}
                    
    except Exception as e:
        return {"executions": [], "error": str(e)}


# --- Feature Discovery API ---

# Feature definitions with requirements
FEATURES = [
    {
        "id": "chat",
        "name": "AI Chat",
        "description": "Chat with your local AI model",
        "icon": "MessageSquare",
        "category": "core",
        "requirements": {
            "services": ["vllm"],
            "vram_gb": 4,
        },
        "enabled_check": lambda services: any(s.id == "vllm" and s.status == "healthy" for s in services),
        "setup_time": "Ready",
        "priority": 1
    },
    {
        "id": "voice",
        "name": "Voice Assistant",
        "description": "Talk to your AI with your voice",
        "icon": "Mic",
        "category": "voice",
        "requirements": {
            "services": ["whisper", "tts", "livekit"],
            "vram_gb": 6,  # Additional VRAM for STT/TTS
        },
        "enabled_check": lambda services: all(
            any(s.id == svc and s.status == "healthy" for s in services)
            for svc in ["whisper", "tts"]
        ),
        "setup_time": "~5 minutes",
        "priority": 2
    },
    {
        "id": "documents",
        "name": "Document Q&A",
        "description": "Upload documents and ask questions",
        "icon": "FileText",
        "category": "productivity",
        "requirements": {
            "services": ["vllm", "qdrant"],
            "vram_gb": 4,
            "disk_gb": 1,
        },
        "enabled_check": lambda services: any(s.id == "qdrant" and s.status == "healthy" for s in services),
        "setup_time": "~2 minutes",
        "priority": 3
    },
    {
        "id": "workflows",
        "name": "Workflow Automation",
        "description": "Automate tasks with AI-powered workflows",
        "icon": "Workflow",
        "category": "productivity",
        "requirements": {
            "services": ["n8n"],
            "vram_gb": 0,
        },
        "enabled_check": lambda services: any(s.id == "n8n" and s.status == "healthy" for s in services),
        "setup_time": "~1 minute",
        "priority": 4
    },
    {
        "id": "images",
        "name": "Image Generation",
        "description": "Generate images with AI",
        "icon": "Image",
        "category": "creative",
        "requirements": {
            "services": [],
            "vram_gb": 12,  # Need significant VRAM for image gen
        },
        "enabled_check": lambda services: False,  # Not yet implemented
        "setup_time": "Coming soon",
        "priority": 5
    },
    {
        "id": "coding",
        "name": "Coding Assistant",
        "description": "AI-powered code completion and review",
        "icon": "Code",
        "category": "development",
        "requirements": {
            "services": ["vllm"],
            "vram_gb": 8,  # Benefits from larger model
        },
        "enabled_check": lambda services: any(s.id == "vllm" and s.status == "healthy" for s in services),
        "setup_time": "Ready (use Coder model)",
        "priority": 6
    }
]


def calculate_feature_status(feature: dict, services: list, gpu_info: Optional[GPUInfo]) -> dict:
    """Calculate whether a feature can be enabled and its status."""
    gpu_vram_gb = (gpu_info.memory_total_mb / 1024) if gpu_info else 0
    gpu_vram_used_gb = (gpu_info.memory_used_mb / 1024) if gpu_info else 0
    gpu_vram_free_gb = gpu_vram_gb - gpu_vram_used_gb
    
    req = feature["requirements"]
    
    # Check if requirements are met
    vram_ok = gpu_vram_gb >= req.get("vram_gb", 0)
    vram_fits = gpu_vram_free_gb >= req.get("vram_gb", 0)
    
    required_services = req.get("services", [])
    services_available = []
    services_missing = []
    
    for svc_id in required_services:
        svc_status = next(
            (s for s in services if s.id == svc_id),
            None
        )
        if svc_status and svc_status.status == "healthy":
            services_available.append(svc_id)
        else:
            services_missing.append(svc_id)
    
    services_ok = len(services_missing) == 0
    
    # Check if actually enabled (running and working)
    try:
        is_enabled = feature["enabled_check"](services)
    except Exception:
        is_enabled = False
    
    # Determine overall status
    if is_enabled:
        status = "enabled"
    elif not vram_ok:
        status = "insufficient_vram"
    elif not services_ok:
        status = "services_needed"
    else:
        status = "available"
    
    return {
        "id": feature["id"],
        "name": feature["name"],
        "description": feature["description"],
        "icon": feature["icon"],
        "category": feature["category"],
        "status": status,
        "enabled": is_enabled,
        "requirements": {
            "vramGb": req.get("vram_gb", 0),
            "vramOk": vram_ok,
            "vramFits": vram_fits,
            "services": required_services,
            "servicesAvailable": services_available,
            "servicesMissing": services_missing,
            "servicesOk": services_ok,
        },
        "setupTime": feature["setup_time"],
        "priority": feature["priority"]
    }


@app.get("/api/features")
async def api_features(api_key: str = Depends(verify_api_key)):
    """
    Get feature discovery data.
    Shows what features are available, enabled, and recommended.
    """
    gpu_info = get_gpu_info()
    service_list = await services()
    
    # Calculate status for each feature
    feature_statuses = [
        calculate_feature_status(f, service_list, gpu_info)
        for f in FEATURES
    ]
    
    # Sort by priority
    feature_statuses.sort(key=lambda x: x["priority"])
    
    # Count by status
    enabled_count = sum(1 for f in feature_statuses if f["enabled"])
    available_count = sum(1 for f in feature_statuses if f["status"] == "available")
    total_count = len(feature_statuses)
    
    # Calculate suggestions (features that could be enabled)
    suggestions = []
    for f in feature_statuses:
        if f["status"] == "available":
            suggestions.append({
                "featureId": f["id"],
                "name": f["name"],
                "message": f"Your hardware can run {f['name']}. Enable it?",
                "action": f"Enable {f['name']}",
                "setupTime": f["setupTime"]
            })
        elif f["status"] == "services_needed":
            missing = ", ".join(f["requirements"]["servicesMissing"])
            suggestions.append({
                "featureId": f["id"],
                "name": f["name"],
                "message": f"{f['name']} needs {missing} to be running.",
                "action": f"Start {missing}",
                "setupTime": f["setupTime"],
                "blocked": True
            })
    
    # Hardware summary
    gpu_vram_gb = (gpu_info.memory_total_mb / 1024) if gpu_info else 0
    
    # Tier-based recommendations
    tier_recommendations = []
    if gpu_vram_gb >= 80:
        tier_recommendations = [
            "Your GPU can run all features simultaneously",
            "Consider enabling Voice + Documents for the full experience",
            "Image generation is supported at full quality"
        ]
    elif gpu_vram_gb >= 24:
        tier_recommendations = [
            "Great GPU for local AI — most features will run well",
            "Voice and Documents work together",
            "Image generation may require model unloading"
        ]
    elif gpu_vram_gb >= 16:
        tier_recommendations = [
            "Solid GPU for core features",
            "Voice works well with the default model",
            "For images, use a smaller chat model"
        ]
    elif gpu_vram_gb >= 8:
        tier_recommendations = [
            "Entry-level GPU — focus on chat first",
            "Voice is possible with a smaller model",
            "Consider using the 7B model for better speed"
        ]
    else:
        tier_recommendations = [
            "Limited GPU memory — chat will work with small models",
            "Consider cloud hybrid mode for better quality"
        ]
    
    return {
        "features": feature_statuses,
        "summary": {
            "enabled": enabled_count,
            "available": available_count,
            "total": total_count,
            "progress": round(enabled_count / total_count * 100) if total_count > 0 else 0
        },
        "suggestions": suggestions[:3],  # Top 3 suggestions
        "recommendations": tier_recommendations,
        "gpu": {
            "name": gpu_info.name if gpu_info else "Unknown",
            "vramGb": round(gpu_vram_gb, 1),
            "tier": get_gpu_tier(gpu_vram_gb)
        }
    }


def get_gpu_tier(vram_gb: float) -> str:
    """Get tier name based on VRAM."""
    if vram_gb >= 80:
        return "Professional"
    elif vram_gb >= 24:
        return "Prosumer"
    elif vram_gb >= 16:
        return "Standard"
    elif vram_gb >= 8:
        return "Entry"
    else:
        return "Minimal"


@app.get("/api/features/{feature_id}/enable")
async def feature_enable_instructions(feature_id: str, api_key: str = Depends(verify_api_key)):
    """
    Get instructions to enable a specific feature.
    """
    feature = next((f for f in FEATURES if f["id"] == feature_id), None)
    if not feature:
        raise HTTPException(status_code=404, detail=f"Feature not found: {feature_id}")
    
    instructions = {
        "chat": {
            "steps": [
                "Chat is already enabled if vLLM is running",
                "Open the Dashboard and click 'Chat' to start"
            ],
            "links": [
                {"label": "Open Chat", "url": "http://localhost:3000"}
            ]
        },
        "voice": {
            "steps": [
                "Ensure Whisper (STT) is running on port 9000",
                "Ensure Kokoro (TTS) is running on port 8880",
                "Start LiveKit for WebRTC",
                "Open the Voice page in the Dashboard"
            ],
            "links": [
                {"label": "Voice Dashboard", "url": "http://localhost:3001/voice"}
            ]
        },
        "documents": {
            "steps": [
                "Ensure Qdrant vector database is running",
                "Enable the 'Document Q&A' workflow",
                "Upload documents via the workflow endpoint"
            ],
            "links": [
                {"label": "Workflows", "url": "http://localhost:3001/workflows"}
            ]
        },
        "workflows": {
            "steps": [
                "Ensure n8n is running on port 5678",
                "Open the Workflows page to see available automations",
                "Click 'Enable' on any workflow to import it"
            ],
            "links": [
                {"label": "n8n Dashboard", "url": "http://localhost:5678"},
                {"label": "Workflows", "url": "http://localhost:3001/workflows"}
            ]
        },
        "images": {
            "steps": [
                "Image generation requires additional setup",
                "Coming soon in a future update"
            ],
            "links": []
        },
        "coding": {
            "steps": [
                "Switch to the Qwen2.5-Coder model for best results",
                "Use the model manager to download and load it",
                "Chat will now be optimized for code"
            ],
            "links": [
                {"label": "Model Manager", "url": "http://localhost:3001/models"}
            ]
        }
    }
    
    return {
        "featureId": feature_id,
        "name": feature["name"],
        "instructions": instructions.get(feature_id, {"steps": [], "links": []})
    }


# --- First-Run Wizard API ---

SETUP_CONFIG_DIR = Path(DATA_DIR) / "config"

# Persona definitions with system prompts
PERSONAS = {
    "general": {
        "name": "General Helper",
        "system_prompt": "You are a friendly and helpful AI assistant. You're knowledgeable, patient, and aim to be genuinely useful. Keep responses clear and conversational.",
        "icon": "💬"
    },
    "coding": {
        "name": "Coding Buddy", 
        "system_prompt": "You are a skilled programmer and technical assistant. You write clean, well-documented code and explain technical concepts clearly. You're precise, thorough, and love solving problems.",
        "icon": "💻"
    },
    "creative": {
        "name": "Creative Writer",
        "system_prompt": "You are an imaginative creative writer and storyteller. You craft vivid descriptions, engaging narratives, and think outside the box. You're expressive and enjoy wordplay.",
        "icon": "🎨"
    }
}


class PersonaRequest(BaseModel):
    persona: str  # "general", "coding", or "creative"


@app.get("/api/setup/status")
async def setup_status(api_key: str = Depends(verify_api_key)):
    """
    Check if this is a first-run scenario.
    Returns first_run=True if setup hasn't been completed.
    """
    setup_complete_file = SETUP_CONFIG_DIR / "setup-complete.json"
    first_run = not setup_complete_file.exists()
    
    # Get current step if in progress
    step = 0
    progress_file = SETUP_CONFIG_DIR / "setup-progress.json"
    if progress_file.exists():
        try:
            with open(progress_file) as f:
                progress = json.load(f)
                step = progress.get("step", 0)
        except Exception:
            pass
    
    # Get persona if already selected
    persona = None
    persona_file = SETUP_CONFIG_DIR / "persona.json"
    if persona_file.exists():
        try:
            with open(persona_file) as f:
                data = json.load(f)
                persona = data.get("persona")
        except Exception:
            pass
    
    return {
        "first_run": first_run,
        "step": step,
        "persona": persona,
        "personas_available": list(PERSONAS.keys())
    }


@app.post("/api/setup/persona")
async def setup_persona(request: PersonaRequest, api_key: str = Depends(verify_api_key)):
    """
    Set the user's chosen persona (assistant type).
    Writes system prompt to config file.
    """
    if request.persona not in PERSONAS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid persona. Choose from: {list(PERSONAS.keys())}"
        )
    
    persona_info = PERSONAS[request.persona]
    
    # Ensure config directory exists
    SETUP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write persona config
    persona_file = SETUP_CONFIG_DIR / "persona.json"
    persona_data = {
        "persona": request.persona,
        "name": persona_info["name"],
        "system_prompt": persona_info["system_prompt"],
        "icon": persona_info["icon"],
        "selected_at": datetime.now(timezone.utc).isoformat()
    }
    
    with open(persona_file, "w") as f:
        json.dump(persona_data, f, indent=2)
    
    # Update progress
    progress_file = SETUP_CONFIG_DIR / "setup-progress.json"
    progress = {"step": 2, "persona_selected": True}
    with open(progress_file, "w") as f:
        json.dump(progress, f)
    
    return {
        "success": True,
        "persona": request.persona,
        "name": persona_info["name"],
        "message": f"Great choice! Your assistant is now a {persona_info['name']}."
    }


@app.post("/api/setup/complete")
async def setup_complete(api_key: str = Depends(verify_api_key)):
    """
    Mark the first-run setup as complete.
    Creates setup-complete.json so future loads skip the wizard.
    """
    # Ensure config directory exists
    SETUP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write completion marker
    complete_file = SETUP_CONFIG_DIR / "setup-complete.json"
    complete_data = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }
    
    with open(complete_file, "w") as f:
        json.dump(complete_data, f, indent=2)
    
    # Clean up progress file
    progress_file = SETUP_CONFIG_DIR / "setup-progress.json"
    if progress_file.exists():
        progress_file.unlink()
    
    return {
        "success": True,
        "redirect": "/",
        "message": "Setup complete! Welcome to Dream Server."
    }


@app.get("/api/setup/persona/{persona_id}")
async def get_persona_info(persona_id: str, api_key: str = Depends(verify_api_key)):
    """Get details about a specific persona."""
    if persona_id not in PERSONAS:
        raise HTTPException(status_code=404, detail=f"Persona not found: {persona_id}")
    
    return {
        "id": persona_id,
        **PERSONAS[persona_id]
    }


@app.get("/api/setup/personas")
async def list_personas(api_key: str = Depends(verify_api_key)):
    """List all available personas."""
    return {
        "personas": [
            {"id": pid, **pdata}
            for pid, pdata in PERSONAS.items()
        ]
    }


# --- Chat API (for QuickWin step) ---

class ChatRequest(BaseModel):
    message: str
    system: Optional[str] = None


def get_active_persona_prompt() -> str:
    """Get the system prompt for the active persona."""
    persona_file = SETUP_CONFIG_DIR / "persona.json"
    if persona_file.exists():
        try:
            with open(persona_file) as f:
                data = json.load(f)
                return data.get("system_prompt", PERSONAS["general"]["system_prompt"])
        except Exception:
            pass
    return PERSONAS["general"]["system_prompt"]


@app.post("/api/chat")
async def chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """
    Simple chat endpoint for the setup wizard QuickWin step.
    Proxies to vLLM's OpenAI-compatible chat completions endpoint.
    """
    
    # Use provided system prompt or the active persona's prompt
    system_prompt = request.system or get_active_persona_prompt()
    
    vllm_url = os.environ.get("VLLM_URL", "http://localhost:8000")
    
    payload = {
        "model": "default",  # vLLM ignores model name when single model loaded
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ],
        "max_tokens": 256,
        "temperature": 0.7
    }
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                f"{vllm_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {"response": response_text, "success": True}
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"vLLM error: {error_text}")
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach vLLM: {e}")


# --- Voice Transcription API (for VoiceTest step) ---

@app.post("/api/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """
    Transcribe audio using Whisper.
    Accepts multipart form data with 'audio' file.
    """
    
    stt_base_url = os.environ.get("STT_BASE_URL", "http://whisper:9000")
    
    try:
        # Read uploaded audio
        audio_data = await audio.read()
        
        # Forward to Whisper
        form_data = aiohttp.FormData()
        form_data.add_field(
            'file',
            audio_data,
            filename=audio.filename or 'audio.webm',
            content_type=audio.content_type or 'audio/webm'
        )
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                f"{stt_base_url}/inference",
                data=form_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "text": data.get("text", ""),
                        "success": True
                    }
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Whisper error: {error_text}")

    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach Whisper: {e}")


# File upload version of transcribe
from fastapi import File, UploadFile


@app.post("/api/voice/transcribe-file")
async def voice_transcribe_file(audio: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """
    Transcribe uploaded audio file using Whisper.
    """
    stt_base_url = os.environ.get("STT_BASE_URL", "http://localhost:9000")
    
    try:
        # Read uploaded audio
        audio_data = await audio.read()
        
        # Forward to Whisper
        form_data = aiohttp.FormData()
        form_data.add_field(
            'file',
            audio_data,
            filename=audio.filename or 'audio.webm',
            content_type=audio.content_type or 'audio/webm'
        )
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                f"{stt_base_url}/inference",
                data=form_data
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "text": data.get("text", ""),
                        "success": True
                    }
                else:
                    error_text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"Whisper error: {error_text}")

    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach Whisper: {e}")


# ============================================
# Storage Endpoint (Settings page)
# ============================================

@app.get("/api/storage")
async def api_storage(api_key: str = Depends(verify_api_key)):
    """Get storage breakdown for Settings page."""
    models_dir = Path(INSTALL_DIR) / "models"
    vector_dir = Path(DATA_DIR) / "qdrant"

    def dir_size_gb(path: Path) -> float:
        if not path.exists():
            return 0.0
        total = 0
        try:
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        except (PermissionError, OSError):
            pass
        return round(total / (1024**3), 2)

    disk = get_disk_usage()
    models_gb = dir_size_gb(models_dir)
    vector_gb = dir_size_gb(vector_dir)

    # Estimate docker images size (not directly measurable without docker socket)
    docker_gb = 0.0

    return {
        "models": {
            "formatted": f"{models_gb:.1f} GB",
            "gb": models_gb,
            "percent": round(models_gb / disk.total_gb * 100, 1) if disk.total_gb else 0
        },
        "vector_db": {
            "formatted": f"{vector_gb:.1f} GB",
            "gb": vector_gb,
            "percent": round(vector_gb / disk.total_gb * 100, 1) if disk.total_gb else 0
        },
        "docker_images": {
            "formatted": "N/A",
            "gb": docker_gb,
            "percent": 0
        },
        "disk": {
            "used_gb": disk.used_gb,
            "total_gb": disk.total_gb,
            "percent": disk.percent
        }
    }


# ============================================
# Version & Update Endpoints (M11)
# ============================================

class VersionInfo(BaseModel):
    current: str
    latest: Optional[str] = None
    update_available: bool = False
    changelog_url: Optional[str] = None
    checked_at: Optional[str] = None


@app.get("/api/version", response_model=VersionInfo, dependencies=[Depends(verify_api_key)])
async def get_version():
    """
    Get current Dream Server version and check for updates.
    Queries GitHub releases API (cached for 1 hour).
    """
    import urllib.request
    import urllib.error
    
    version_file = Path(INSTALL_DIR) / ".version"
    current = "0.0.0"
    
    # Read current version
    if version_file.exists():
        current = version_file.read_text().strip()
    
    result = {
        "current": current,
        "latest": None,
        "update_available": False,
        "changelog_url": None,
        "checked_at": datetime.now(timezone.utc).isoformat() + "Z"
    }
    
    # Check GitHub for latest version (best effort)
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/Light-Heart-Labs/Lighthouse-AI/releases/latest",
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            latest = data.get("tag_name", "").lstrip("v")
            
            if latest:
                result["latest"] = latest
                result["changelog_url"] = data.get("html_url")
                
                # Compare versions (simple semver)
                current_parts = [int(x) for x in current.split(".") if x.isdigit()][:3]
                latest_parts = [int(x) for x in latest.split(".") if x.isdigit()][:3]
                
                # Pad with zeros
                current_parts += [0] * (3 - len(current_parts))
                latest_parts += [0] * (3 - len(latest_parts))
                
                result["update_available"] = latest_parts > current_parts
                
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        # Fail silently — update check is best-effort
        result["checked_at"] = datetime.now(timezone.utc).isoformat() + "Z"
    
    return result


@app.get("/api/releases/manifest")
async def get_release_manifest():
    """
    Get release manifest with version history and changelogs.
    Returns structured release information for the dashboard.
    """
    import urllib.request
    import urllib.error
    
    try:
        # Query GitHub releases API for last 5 releases
        req = urllib.request.Request(
            "https://api.github.com/repos/Light-Heart-Labs/Lighthouse-AI/releases?per_page=5",
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            releases = json.loads(resp.read())
            
            manifest = {
                "releases": [
                    {
                        "version": r.get("tag_name", "").lstrip("v"),
                        "date": r.get("published_at", ""),
                        "title": r.get("name", ""),
                        "changelog": r.get("body", "")[:500] + "..." if len(r.get("body", "")) > 500 else r.get("body", ""),
                        "url": r.get("html_url", ""),
                        "prerelease": r.get("prerelease", False)
                    }
                    for r in releases
                ],
                "checked_at": datetime.now(timezone.utc).isoformat() + "Z"
            }
            return manifest
            
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        # Return fallback with current version
        version_file = Path(INSTALL_DIR) / ".version"
        current = "0.0.0"
        if version_file.exists():
            current = version_file.read_text().strip()
        
        return {
            "releases": [{
                "version": current,
                "date": datetime.now(timezone.utc).isoformat() + "Z",
                "title": f"Dream Server {current}",
                "changelog": "Release information unavailable. Check GitHub directly.",
                "url": "https://github.com/Light-Heart-Labs/Lighthouse-AI/releases",
                "prerelease": False
            }],
            "checked_at": datetime.now(timezone.utc).isoformat() + "Z",
            "error": "Could not fetch release information"
        }


class UpdateAction(BaseModel):
    action: str  # "check", "backup", "update"


@app.post("/api/update")
async def trigger_update(action: UpdateAction, background_tasks: BackgroundTasks, api_key: str = Depends(verify_api_key)):
    """
    Trigger update actions via dashboard.
    
    Actions:
      - check: Run version check
      - backup: Create manual backup
      - update: Start full update process (async)
    """
    # Look for dream-update.sh in repo root scripts/ (not dream-server/scripts/)
    script_path = Path(INSTALL_DIR).parent / "scripts" / "dream-update.sh"
    
    if not script_path.exists():
        # Fallback: check if install.sh exists to determine correct path
        install_script = Path(INSTALL_DIR) / "install.sh"
        if install_script.exists():
            # We're in the dream-server directory, go up one level
            script_path = Path(INSTALL_DIR).parent / "scripts" / "dream-update.sh"
        else:
            # We're at repo root
            script_path = Path(INSTALL_DIR) / "scripts" / "dream-update.sh"
    
    if not script_path.exists():
        raise HTTPException(
            status_code=501,
            detail=f"dream-update.sh not found at {script_path}. Update system not installed."
        )
    
    if action.action == "check":
        # Run check and return result
        try:
            result = subprocess.run(
                [str(script_path), "check"],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Exit code 2 means update available
            update_available = result.returncode == 2
            return {
                "success": True,
                "update_available": update_available,
                "output": result.stdout + result.stderr
            }
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Update check timed out")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Check failed: {e}")
    
    elif action.action == "backup":
        # Create backup synchronously
        try:
            result = subprocess.run(
                [str(script_path), "backup", f"dashboard-{datetime.now().strftime('%Y%m%d-%H%M%S')}"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout + result.stderr
            }
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Backup timed out")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Backup failed: {e}")
    
    elif action.action == "update":
        # Start update in background (takes time, risky to wait)
        def run_update():
            subprocess.run([str(script_path), "update"], capture_output=True)
        
        background_tasks.add_task(run_update)
        return {
            "success": True,
            "message": "Update started in background. Check logs for progress."
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")


# --- Agent Monitoring Endpoints ---

@app.get("/api/agents/metrics")
async def get_agent_metrics(api_key: str = Depends(verify_api_key)):
    """
    Get comprehensive agent monitoring metrics.

    Returns:
      - Agent session counts and health
      - Cluster node status
      - Token usage statistics (24h)
      - Throughput history (15 min)
    """
    return get_full_agent_metrics()


@app.get("/api/agents/metrics.html")
async def get_agent_metrics_html(api_key: str = Depends(verify_api_key)):
    """
    Get agent metrics as HTML fragment for htmx.
    """
    metrics = get_full_agent_metrics()
    
    # Determine status classes
    cluster_class = "status-ok" if metrics["cluster"]["failover_ready"] else "status-warn"
    
    html = f"""
    <div class="grid">
        <!-- Cluster Status -->
        <article class="metric-card">
            <div class="metric-label">Cluster Status</div>
            <div class="metric-value {cluster_class}">
                {metrics["cluster"]["active_gpus"]}/{metrics["cluster"]["total_gpus"]} GPUs
            </div>
            <p style="margin: 0; font-size: 0.875rem;">
                Failover: {"Ready ✅" if metrics["cluster"]["failover_ready"] else "Single GPU ⚠️"}
            </p>
        </article>
        
        <!-- Session Count -->
        <article class="metric-card">
            <div class="metric-label">Active Sessions</div>
            <div class="metric-value">{metrics["agent"]["session_count"]}</div>
            <p style="margin: 0; font-size: 0.875rem;">
                Updated: {metrics["agent"]["last_update"].split("T")[1][:8]}
            </p>
        </article>
        
        <!-- Token Usage -->
        <article class="metric-card">
            <div class="metric-label">Token Usage (24h)</div>
            <div class="metric-value">{metrics["tokens"]["total_tokens_24h"]//1000}K</div>
            <p style="margin: 0; font-size: 0.875rem;">
                ${metrics["tokens"]["total_cost_24h"]:.4f} | {metrics["tokens"]["requests_24h"]} reqs
            </p>
        </article>
        
        <!-- Throughput -->
        <article class="metric-card">
            <div class="metric-label">Throughput</div>
            <div class="metric-value">{metrics["throughput"]["current"]:.1f}</div>
            <p style="margin: 0; font-size: 0.875rem;">
                tokens/sec (avg: {metrics["throughput"]["average"]:.1f})
            </p>
        </article>
    </div>
    
    <!-- Top Models -->
    {"<article class='metric-card'><h4>Top Models (24h)</h4><table><thead><tr><th>Model</th><th>Tokens</th><th>Requests</th></tr></thead><tbody>" + "".join([f"<tr><td>{m['model']}</td><td>{m['tokens']//1000}K</td><td>{m['requests']}</td></tr>" for m in metrics['tokens']['top_models']]) + "</tbody></table></article>" if metrics['tokens']['top_models'] else ""}
    """
    
    return HTMLResponse(content=html)


@app.get("/api/agents/cluster")
async def get_cluster_status(api_key: str = Depends(verify_api_key)):
    """Get cluster health and node status"""
    await cluster_status.refresh()
    return cluster_status.to_dict()


@app.get("/api/agents/tokens")
async def get_token_usage(api_key: str = Depends(verify_api_key)):
    """Get token usage statistics from token monitor"""
    await token_usage.refresh()
    return token_usage.to_dict()


@app.get("/api/agents/throughput")
async def get_throughput(api_key: str = Depends(verify_api_key)):
    """Get throughput metrics (tokens/sec)"""
    return throughput.get_stats()


# --- Setup Wizard Endpoints ---

@app.post("/api/setup/test")
async def run_setup_diagnostics(api_key: str = Depends(verify_api_key)):
    """
    Run diagnostic tests for setup wizard.
    Streams output as SSE for real-time progress.
    """
    from fastapi.responses import StreamingResponse
    import subprocess
    
    script_path = Path(INSTALL_DIR) / "scripts" / "dream-test-functional.sh"
    if not script_path.exists():
        script_path = Path(os.getcwd()) / "dream-test-functional.sh"
    
    if not script_path.exists():
        async def error_stream():
            yield "Diagnostic script not found. Running basic connectivity tests...\n"
            # Fallback: basic service checks
            async with aiohttp.ClientSession() as session:
                services = [
                    ("vLLM", "http://vllm:8000/v1/models"),
                    ("Open WebUI", "http://open-webui:8080/"),
                    ("Whisper (STT)", "http://whisper:9000/"),
                    ("Kokoro (TTS)", "http://tts:8880/health"),
                    ("n8n", "http://n8n:5678/healthz"),
                    ("LiveKit", "http://livekit:7880/"),
                    ("OpenClaw", "http://openclaw:18789/"),
                ]
                for name, url in services:
                    try:
                        async with session.get(url, timeout=5) as resp:
                            status = "✓" if resp.status == 200 else "✗"
                            yield f"{status} {name}: {resp.status}\n"
                    except Exception as e:
                        yield f"✗ {name}: {e}\n"
            yield "\nSetup complete!\n"
        
        return StreamingResponse(error_stream(), media_type="text/plain")
    
    def run_tests():
        """Generator for test output"""
        process = subprocess.Popen(
            ["bash", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        for line in process.stdout:
            yield line
        
        process.wait()
        yield f"\n{'All tests passed!' if process.returncode == 0 else 'Some tests failed.'}\n"
    
    return StreamingResponse(run_tests(), media_type="text/plain")


# --- Privacy Shield Management (Punch List #12) ---

class PrivacyShieldStatus(BaseModel):
    enabled: bool
    container_running: bool
    port: int
    target_api: str
    pii_cache_enabled: bool
    message: str


@app.get("/api/privacy-shield/status", response_model=PrivacyShieldStatus)
async def get_privacy_shield_status(api_key: str = Depends(verify_api_key)):
    """
    Get Privacy Shield status and configuration.
    
    Returns whether Privacy Shield is enabled, container status,
    and current configuration.
    """
    
    shield_port = int(os.environ.get("SHIELD_PORT", "8085"))
    shield_url = f"http://privacy-shield:{shield_port}"
    
    # Check if container is running
    container_running = False
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "--filter", "name=dream-privacy-shield", "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        container_running = "dream-privacy-shield" in stdout.decode()
    except Exception:
        pass
    
    # Check if service is responding
    service_healthy = False
    if container_running:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"{shield_url}/health") as resp:
                    service_healthy = resp.status == 200
        except Exception:
            pass
    
    return PrivacyShieldStatus(
        enabled=container_running and service_healthy,
        container_running=container_running,
        port=shield_port,
        target_api=os.environ.get("TARGET_API_URL", "http://vllm:8000/v1"),
        pii_cache_enabled=os.environ.get("PII_CACHE_ENABLED", "true").lower() == "true",
        message="Privacy Shield is active" if (container_running and service_healthy) else "Privacy Shield is not running. Enable with --profile privacy or --profile full"
    )


class PrivacyShieldToggle(BaseModel):
    enable: bool


@app.post("/api/privacy-shield/toggle")
async def toggle_privacy_shield(request: PrivacyShieldToggle, api_key: str = Depends(verify_api_key)):
    """
    Enable or disable Privacy Shield.
    
    This starts or stops the privacy-shield container.
    Note: Requires docker-compose profile to include 'privacy'.
    """
    try:
        if request.enable:
            # Start privacy-shield container
            proc = await asyncio.create_subprocess_exec(
                "docker-compose", "--profile", "privacy", "up", "-d", "privacy-shield",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=INSTALL_DIR
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0:
                return {"success": True, "message": "Privacy Shield started. PII scrubbing is now active."}
            else:
                return {"success": False, "message": f"Failed to start: {stderr.decode()}", "hint": "Ensure docker-compose.yml has 'privacy' profile for privacy-shield service"}
        else:
            # Stop privacy-shield container
            proc = await asyncio.create_subprocess_exec(
                "docker-compose", "stop", "privacy-shield",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=INSTALL_DIR
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0:
                return {"success": True, "message": "Privacy Shield stopped."}
            else:
                return {"success": False, "message": f"Failed to stop: {stderr.decode()}"}
                
    except FileNotFoundError:
        return {"success": False, "message": "Docker not available", "note": "Running in development mode without Docker"}
    except asyncio.TimeoutError:
        return {"success": False, "message": "Operation timed out"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


@app.get("/api/privacy-shield/stats")
async def get_privacy_shield_stats(api_key: str = Depends(verify_api_key)):
    """
    Get Privacy Shield usage statistics.
    
    Returns anonymization metrics, cache stats, and request counts.
    """
    shield_port = int(os.environ.get("SHIELD_PORT", "8085"))
    shield_url = f"http://privacy-shield:{shield_port}"
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{shield_url}/stats") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"error": "Privacy Shield not responding", "status": resp.status}
    except Exception as e:
        return {"error": "Cannot reach Privacy Shield", "detail": str(e), "enabled": False}


# --- Organization API (Token Spy M12) ---

class OrganizationCreate(BaseModel):
    name: str
    slug: Optional[str] = None

@app.get("/api/organizations")
async def list_organizations(api_key: str = Depends(verify_api_key)):
    """List organizations for the authenticated user."""
    # For dev mode, return empty list or mock data
    return {
        "organizations": [],
        "total": 0,
        "limit": 100,
        "offset": 0
    }

@app.post("/api/organizations")
async def create_organization(
    req: OrganizationCreate,
    api_key: str = Depends(verify_api_key)
):
    """Create a new organization."""
    import uuid
    from datetime import datetime, timezone as dt

    org_id = str(uuid.uuid4())
    slug = req.slug or req.name.lower().replace(" ", "-")
    created_at = datetime.now(timezone.utc)

    return {
        "id": org_id,
        "name": req.name,
        "slug": slug,
        "plan": "free",
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat()
    }


# --- Startup Event ---

@app.on_event("startup")
async def startup_event():
    """Start background metrics collection"""
    asyncio.create_task(collect_metrics())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3002)
