"""
Agent Monitoring Dashboard - Backend
FastAPI server for real-time GPU, cluster, and session metrics.

Phase 3: Complete frontend with htmx + Chart.js
Port: 8080
"""

import subprocess
import json
import time
import os
import secrets
import html
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import httpx
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path

# Security: API Key Authentication
DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY")
if not DASHBOARD_API_KEY:
    DASHBOARD_API_KEY = secrets.token_urlsafe(32)
    print(f"WARNING: DASHBOARD_API_KEY not set. Generated temporary key: {DASHBOARD_API_KEY[:8]}...")

security_scheme = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """Verify API key for protected endpoints."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not secrets.compare_digest(credentials.credentials, DASHBOARD_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return credentials.credentials

app = FastAPI(title="Agent Dashboard", version="3.0.0")

# Config
DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"

# OpenClaw Gateway configuration (for agent status)
# Set OPENCLAW_GATEWAY_URL to your gateway endpoint, or leave empty to disable
OPENCLAW_GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "")

# Local sessions directory fallback (for development)
# Set OPENCLAW_SESSIONS_DIR to a local path if not using gateway
OPENCLAW_SESSIONS_DIR = os.environ.get("OPENCLAW_SESSIONS_DIR", "")

# Metrics cache with TTL
_metrics_cache: Dict[str, Any] = {}
_cache_timestamp: float = 0
CACHE_TTL_SECONDS = 2

# Historical data for charts (in-memory)
_gpu_history: Dict[int, List[Dict]] = {0: [], 1: []}
_throughput_history: List[Dict] = []
MAX_HISTORY_POINTS = 60  # 5 minutes at 5s intervals


def get_cached_or_fetch(key: str, fetch_fn):
    """Get cached value or fetch new one if expired."""
    global _cache_timestamp
    now = time.time()
    if now - _cache_timestamp > CACHE_TTL_SECONDS:
        _metrics_cache.clear()
        _cache_timestamp = now
    if key not in _metrics_cache:
        try:
            _metrics_cache[key] = fetch_fn()
        except Exception as e:
            _metrics_cache[key] = {"error": str(e)}
    return _metrics_cache[key]


def store_gpu_history(gpus: List[Dict]):
    """Store GPU metrics for historical charts."""
    timestamp = datetime.now().isoformat()
    for gpu in gpus:
        idx = gpu.get("index", 0)
        if idx in _gpu_history:
            _gpu_history[idx].append({
                "timestamp": timestamp,
                "utilization": gpu.get("utilization_percent", 0),
                "memory_percent": (gpu.get("memory_used_mb", 0) / max(gpu.get("memory_total_mb", 1), 1)) * 100,
                "temperature": gpu.get("temperature_c", 0)
            })
            # Prune old data
            if len(_gpu_history[idx]) > MAX_HISTORY_POINTS:
                _gpu_history[idx] = _gpu_history[idx][-MAX_HISTORY_POINTS:]


def store_throughput_history(tps: float):
    """Store throughput metrics for historical charts."""
    _throughput_history.append({
        "timestamp": datetime.now().isoformat(),
        "tokens_per_sec": tps
    })
    if len(_throughput_history) > MAX_HISTORY_POINTS:
        _throughput_history.pop(0)


@app.get("/api/health")
def health_check():
    """Basic health endpoint (public)."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/gpu", dependencies=[Depends(verify_api_key)])
async def get_gpu_stats():
    """Get GPU stats from nvidia-smi."""
    def fetch():
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            gpus = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "temperature_c": float(parts[2]) if parts[2] else None,
                        "utilization_percent": float(parts[3]) if parts[3] else None,
                        "memory_used_mb": float(parts[4]) if parts[4] else None,
                        "memory_total_mb": float(parts[5]) if parts[5] else None,
                    })
            # Store for history
            store_gpu_history(gpus)
            return {"gpus": gpus, "count": len(gpus)}
        except Exception as e:
            return {"error": str(e), "gpus": []}
    return get_cached_or_fetch("gpu", fetch)


@app.get("/api/cluster", dependencies=[Depends(verify_api_key)])
async def get_cluster_status():
    """Get cluster status from smart proxy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:9199/status")
            return response.json()
    except Exception as e:
        return {"error": str(e), "nodes": []}


@app.get("/api/vllm", dependencies=[Depends(verify_api_key)])
async def get_vllm_metrics():
    """Get vLLM Prometheus-style metrics."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/metrics")
            text = response.text
            # Parse key metrics from Prometheus format
            metrics = {}
            for line in text.split("\n"):
                if "vllm:token_generation_tokens_total" in line and not line.startswith("#"):
                    metrics["tokens_generated_total"] = float(line.split()[-1])
                elif "vllm:prompt_tokens_total" in line and not line.startswith("#"):
                    metrics["prompt_tokens_total"] = float(line.split()[-1])
                elif "vllm:generation_tokens_per_second" in line and not line.startswith("#"):
                    metrics["tokens_per_second_current"] = float(line.split()[-1])
                    store_throughput_history(metrics["tokens_per_second_current"])
                elif "vllm:num_requests_running" in line and not line.startswith("#"):
                    metrics["requests_running"] = int(float(line.split()[-1]))
                elif "vllm:num_requests_waiting" in line and not line.startswith("#"):
                    metrics["requests_waiting"] = int(float(line.split()[-1]))
            return metrics
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/agents", dependencies=[Depends(verify_api_key)])
async def get_agent_status():
    """Get sub-agent status from OpenClaw gateway session data."""
    import httpx
    import json
    
    # Query OpenClaw gateway sessions endpoint
    # Configure via OPENCLAW_GATEWAY_URL env var
    sessions_data = {"sessions": []}
    
    if OPENCLAW_GATEWAY_URL:
        sessions_endpoint = f"{OPENCLAW_GATEWAY_URL}/api/sessions"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(sessions_endpoint)
                sessions_data = response.json()
        except Exception as e:
            # Gateway unavailable - will fall through to local fallback
            pass
    
    # Fallback to local session files if gateway unavailable or not configured
    if not sessions_data.get("sessions") and OPENCLAW_SESSIONS_DIR:
        sessions_dir = Path(OPENCLAW_SESSIONS_DIR)
        if sessions_dir.exists():
            try:
                sessions_file = sessions_dir / "sessions.json"
                if sessions_file.exists():
                    with open(sessions_file) as f:
                        local_sessions = json.load(f)
                        # Transform to expected format
                        for session_key, session_info in local_sessions.items():
                            sessions_data["sessions"].append({
                                "id": session_key,
                                "info": session_info
                            })
            except Exception:
                pass
    
    # Map OpenClaw sessions to dashboard agent format
    agents = []
    
    # Agent mapping configuration
    # Set AGENT_ID_MAP to a JSON string to configure agent display names
    # Example: '{"agent:main:discord:channel:123": {"id": "agent-1", "name": "Agent 1"}}'
    agent_id_map = {}
    agent_map_env = os.environ.get("AGENT_ID_MAP", "")
    if agent_map_env:
        try:
            agent_id_map = json.loads(agent_map_env)
        except json.JSONDecodeError:
            pass  # Invalid JSON, use empty map
    
    # Process sessions from gateway or local
    for session in sessions_data.get("sessions", []):
        session_id = session.get("id", "")
        session_info = session.get("info", {})
        
        # Check if this is a known agent
        if session_id in agent_id_map:
            agent_info = agent_id_map[session_id]
            
            # Calculate status from session data
            status = "idle"
            current_task = "No recent activity"
            tasks_completed = 0
            uptime_seconds = 0
            
            # Get metrics from session data if available
            last_activity = session_info.get("lastChannel")
            if last_activity:
                status = "active" if session_info.get("updatedAt") else "idle"
                current_task = f"Last active in {last_activity}"
            
            # Extract token usage if available
            input_tokens = session_info.get("inputTokens", 0)
            if input_tokens:
                tasks_completed = input_tokens // 1000  # Approximate task count
            
            # Calculate uptime from last update
            updated_at = session_info.get("updatedAt", 0)
            if updated_at:
                import time
                now_ms = int(time.time() * 1000)
                uptime_seconds = (now_ms - updated_at) // 1000
            
            agents.append({
                "id": agent_info["id"],
                "name": agent_info["name"],
                "status": status,
                "node": agent_info["node"],
                "tasks_completed": tasks_completed,
                "uptime_seconds": uptime_seconds,
                "current_task": current_task,
                "description": agent_info["description"]
            })
    
    # If no sessions found, return empty list or default demo agents
    # Configure demo agents via DEMO_AGENTS env var (JSON array)
    if not agents:
        demo_agents_env = os.environ.get("DEMO_AGENTS", "")
        if demo_agents_env:
            try:
                agents = json.loads(demo_agents_env)
            except json.JSONDecodeError:
                agents = []
        # If no demo agents configured, return empty list
        # (no hardcoded default agents for public release)
    
    return {"agents": agents, "total": len(agents)}


@app.get("/api/errors", dependencies=[Depends(verify_api_key)])
async def get_recent_errors():
    """Get recent errors from logs."""
    # TODO: Parse actual error logs
    # For now, return empty or mock data
    errors = []
    return {"errors": errors, "total": len(errors)}


@app.get("/api/metrics", dependencies=[Depends(verify_api_key)])
async def get_all_metrics():
    """Get all metrics in one call."""
    gpu = await get_gpu_stats()
    cluster = await get_cluster_status()
    vllm = await get_vllm_metrics()
    agents = await get_agent_status()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gpu": gpu,
        "cluster": cluster,
        "vllm": vllm,
        "agents": agents
    }


@app.get("/api/history/gpu", dependencies=[Depends(verify_api_key)])
def get_gpu_history():
    """Get historical GPU utilization data."""
    return {
        "gpu0": _gpu_history.get(0, []),
        "gpu1": _gpu_history.get(1, [])
    }


@app.get("/api/history/throughput", dependencies=[Depends(verify_api_key)])
def get_throughput_history():
    """Get historical throughput data."""
    return {"history": _throughput_history}


# ============================================
# HTMX Fragment Endpoints
# ============================================

def render_gpu_cluster(gpu_data: dict, cluster_data: dict) -> str:
    """Render GPU and cluster cards HTML fragment."""
    html_parts = []
    
    # GPU cards
    gpus = gpu_data.get("gpus", [])
    
    # Determine node IPs for display
    node_ips = {0: "node-0", 1: "node-1"}
    
    for gpu in gpus:
        idx = gpu.get("index", 0)
        mem_used = gpu.get("memory_used_mb", 0)
        mem_total = gpu.get("memory_total_mb", 1)
        mem_pct = (mem_used / max(mem_total, 1)) * 100
        temp = gpu.get("temperature_c", 0)
        util = gpu.get("utilization_percent", 0)
        name = gpu.get("name", "Unknown GPU")
        node_ip = node_ips.get(idx, "")
        
        # Bar color based on usage
        bar_class = ""
        if mem_pct > 90:
            bar_class = "danger"
        elif mem_pct > 75:
            bar_class = "warning"
        
        # Temperature color
        temp_class = "status-ok"
        if temp > 80:
            temp_class = "status-error"
        elif temp > 70:
            temp_class = "status-warn"
        
        # Escape dynamic values to prevent XSS
        escaped_node_ip = html.escape(str(node_ip))
        escaped_name = html.escape(str(name))
        
        html_parts.append(f"""
        <article class="metric-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <p class="metric-label" style="margin:0;">GPU {idx} <span class="node-badge">{escaped_node_ip}</span></p>
            </div>
            <p style="margin:0.25rem 0 0 0; font-size:0.9rem; color:var(--secondary);">{escaped_name}</p>
            <div class="gpu-bar">
                <div class="gpu-bar-fill {bar_class}" style="width: {mem_pct:.1f}%"></div>
            </div>
            <p class="metric-sub">{mem_used:.0f} / {mem_total:.0f} MB ({mem_pct:.1f}%)</p>
            <div class="stats-row">
                <span class="stat-item {temp_class}">🌡️ {temp:.0f}°C</span>
                <span class="stat-item">⚡ {util:.0f}%</span>
            </div>
        </article>
        """)
    
    # Handle case with no GPUs
    if not gpus:
        html_parts.append("""
        <article class="metric-card">
            <p class="metric-label">GPU Status</p>
            <p class="metric-value status-error">No GPUs detected</p>
            <p class="metric-sub">nvidia-smi may not be available</p>
        </article>
        """)
    
    # Cluster health card
    nodes_dict = cluster_data.get("nodes", {})
    # Convert to list for iteration
    nodes = list(nodes_dict.values()) if isinstance(nodes_dict, dict) else nodes_dict
    healthy = sum(1 for n in nodes if n.get("healthy", False))
    total = len(nodes) if nodes else 2  # Default to 2 expected nodes
    failover_ready = cluster_data.get("failover_ready", False) or healthy > 1
    active_node = cluster_data.get("active_node", "primary")
    
    if healthy == total and total > 0:
        status_class = "status-ok"
        status_icon = "✅"
        status_text = "All nodes up"
    elif healthy > 0:
        status_class = "status-warn"
        status_icon = "⚠️"
        status_text = f"{healthy}/{total} nodes up"
    else:
        status_class = "status-error"
        status_icon = "❌"
        status_text = "Cluster down"
    
    failover_status = "Ready" if failover_ready else "Not Ready"
    failover_class = "status-ok" if failover_ready else "status-warn"
    
    html_parts.append(f"""
    <article class="metric-card">
        <p class="metric-label">Cluster Health</p>
        <p class="metric-value {status_class}" style="font-size:1.5rem;">{status_icon} {status_text}</p>
        <p class="metric-sub">{len(gpus)} GPUs active</p>
        <div class="stats-row">
            <span class="stat-item {failover_class}">Failover: {failover_status}</span>
        </div>
    </article>
    """)
    
    # Add data attributes for JS chart updates
    gpu0_util = gpus[0].get("utilization_percent", 0) if len(gpus) > 0 else 0
    gpu1_util = gpus[1].get("utilization_percent", 0) if len(gpus) > 1 else 0
    
    return f'<div id="gpu-cluster-container" data-gpu0-util="{gpu0_util}" data-gpu1-util="{gpu1_util}" style="display:contents;">' + "".join(html_parts) + '</div>'


def render_sessions(vllm_data: dict) -> str:
    """Render session stats HTML fragment."""
    running = vllm_data.get("requests_running", 0)
    waiting = vllm_data.get("requests_waiting", 0)
    
    queue_status = f'<span class="status-warn">{waiting} waiting</span>' if waiting > 0 else '<span class="status-ok">Queue clear</span>'
    
    return f"""
    <p class="metric-label">Active Sessions</p>
    <p class="metric-value">{running}</p>
    <div class="stats-row">
        <span class="stat-item">Queue: {queue_status}</span>
    </div>
    """


def render_tasks(vllm_data: dict) -> str:
    """Render task stats HTML fragment."""
    tokens_gen = vllm_data.get("tokens_generated_total", 0)
    tokens_prompt = vllm_data.get("prompt_tokens_total", 0)
    tps = vllm_data.get("tokens_per_second_current", 0)
    
    tps_class = "status-ok" if tps > 50 else "status-warn" if tps > 10 else "status-unknown"
    
    return f"""
    <p class="metric-label">Task Stats (24h)</p>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
        <div>
            <p class="metric-value" style="font-size:1.25rem;">{tokens_gen:,.0f}</p>
            <p class="metric-sub">Tokens Generated</p>
        </div>
        <div>
            <p class="metric-value" style="font-size:1.25rem;">{tokens_prompt:,.0f}</p>
            <p class="metric-sub">Prompt Tokens</p>
        </div>
    </div>
    <p class="metric-sub {tps_class}" style="margin-top:0.5rem;">Current: {tps:.1f} tokens/sec</p>
    """


def render_agents(agents_data: dict) -> str:
    """Render sub-agent status table HTML fragment."""
    agents = agents_data.get("agents", [])
    
    if not agents:
        return """
        <table class="agent-table">
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Node</th>
                    <th>Tasks</th>
                    <th>Uptime</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="5" style="text-align:center; color:var(--muted-color);">
                        No active agents
                    </td>
                </tr>
            </tbody>
        </table>
        """
    
    rows = []
    for agent in agents:
        status = agent.get("status", "unknown")
        status_class = {
            "active": "ok",
            "idle": "warn", 
            "error": "error"
        }.get(status, "unknown")
        
        uptime_sec = agent.get("uptime_seconds", 0)
        if uptime_sec >= 86400:
            uptime_str = f"{uptime_sec // 86400}d {(uptime_sec % 86400) // 3600}h"
        elif uptime_sec >= 3600:
            uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m"
        else:
            uptime_str = f"{uptime_sec // 60}m {uptime_sec % 60}s"
        
        row_class = "agent-row-active" if status == "active" else ""
        node_badge_class = "primary" if agent.get("node") == "node-0" else ""
        
        # XSS protection: escape all dynamic values (B5 fix)
        agent_name = html.escape(str(agent.get("name", "Unknown")))
        current_task = html.escape(str(agent.get("current_task", "")))
        node = html.escape(str(agent.get("node", "?")))
        
        rows.append(f"""
        <tr class="{row_class}">
            <td>
                <strong>{agent_name}</strong>
                <br><small style="color:var(--muted-color)">{current_task}</small>
            </td>
            <td>
                <span class="status-indicator {status_class}"></span>
                {status.capitalize()}
            </td>
            <td><span class="node-badge {node_badge_class}">{node}</span></td>
            <td>{agent.get("tasks_completed", 0):,}</td>
            <td>{uptime_str}</td>
        </tr>
        """)
    
    return f"""
    <table class="agent-table">
        <thead>
            <tr>
                <th>Agent</th>
                <th>Status</th>
                <th>Node</th>
                <th>Tasks</th>
                <th>Uptime</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    """


def render_errors(errors_data: dict) -> str:
    """Render recent errors HTML fragment."""
    errors = errors_data.get("errors", [])
    
    if not errors:
        return '<p style="color:var(--muted-color); text-align:center; padding:1rem;">✅ No recent errors</p>'
    
    items = []
    for error in errors[:10]:  # Max 10 errors
        # XSS protection: escape all dynamic values (B5 fix)
        timestamp = html.escape(str(error.get("timestamp", "")))
        message = html.escape(str(error.get("message", "Unknown error")))
        items.append(f"""
        <div class="error-item">
            <span class="error-timestamp">{timestamp}</span>
            {message}
        </div>
        """)
    
    return "".join(items)


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
def get_dashboard():
    """Serve the main dashboard HTML from template."""
    template_path = TEMPLATES_DIR / "index.html"
    try:
        with open(template_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"""
        <html>
        <body>
            <h1>Dashboard template not found</h1>
            <p>Expected: {template_path}</p>
            <p>Current dir: {os.getcwd()}</p>
        </body>
        </html>
        """


@app.get("/api/fragments/gpu-cluster", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def get_gpu_cluster_fragment():
    """HTMX fragment for GPU and cluster cards."""
    gpu = await get_gpu_stats()
    cluster = await get_cluster_status()
    return render_gpu_cluster(gpu, cluster)


@app.get("/api/fragments/sessions", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def get_sessions_fragment():
    """HTMX fragment for session stats."""
    vllm = await get_vllm_metrics()
    return render_sessions(vllm)


@app.get("/api/fragments/tasks", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def get_tasks_fragment():
    """HTMX fragment for task stats."""
    vllm = await get_vllm_metrics()
    return render_tasks(vllm)


@app.get("/api/fragments/agents", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def get_agents_fragment():
    """HTMX fragment for sub-agent status table."""
    agents = await get_agent_status()
    return render_agents(agents)


@app.get("/api/fragments/errors", response_class=HTMLResponse, dependencies=[Depends(verify_api_key)])
async def get_errors_fragment():
    """HTMX fragment for recent errors."""
    errors = await get_recent_errors()
    return render_errors(errors)


# Static files (if any custom CSS/JS)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    print(f"Starting Agent Dashboard on port 8080...")
    print(f"Templates: {TEMPLATES_DIR}")
    print(f"Static: {STATIC_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
