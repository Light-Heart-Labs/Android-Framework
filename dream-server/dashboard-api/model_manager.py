"""
Model Manager API for M2

Provides endpoints for downloading, managing, and switching local LLM models.
Integrates with HuggingFace Hub and vLLM.

Usage:
    python model_manager.py
    
Endpoints:
    GET  /api/models/available
    GET  /api/models/downloaded
    POST /api/models/download
    POST /api/models/switch
    DELETE /api/models/{model_id}
"""

import os
import json
import subprocess
import shutil
import asyncio
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from pathlib import Path

# Optional huggingface_hub for actual model downloads
try:
    from huggingface_hub import snapshot_download, hf_hub_download
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

app = FastAPI(title="Model Manager", description="Manage local LLM models")

# Track download progress
download_status: Dict[str, Dict] = {}

# Model registry - available models with metadata
# New format uses structured entries with standardized fields
# Old format (flat dict) is still supported for backward compatibility
MODEL_REGISTRY = {
    "Qwen/Qwen2.5-0.5B-Instruct": {
        "model_path": "Qwen/Qwen2.5-0.5B-Instruct",
        "tokenizer_path": "Qwen/Qwen2.5-0.5B-Instruct",
        "model_name": "Qwen 2.5 0.5B",
        "context_size": 32768,
        "quantization": None,
        "size_gb": 1.0,
        "min_vram_gb": 2,
        "description": "Tiny model for testing",
        "recommended_for": "Testing, debugging"
    },
    "Qwen/Qwen2.5-1.5B-Instruct": {
        "model_path": "Qwen/Qwen2.5-1.5B-Instruct",
        "tokenizer_path": "Qwen/Qwen2.5-1.5B-Instruct",
        "model_name": "Qwen 2.5 1.5B",
        "context_size": 32768,
        "quantization": None,
        "size_gb": 3.0,
        "min_vram_gb": 4,
        "description": "Small model for low-VRAM systems",
        "recommended_for": "Edge deployment, Pi 5"
    },
    "Qwen/Qwen2.5-7B-Instruct-AWQ": {
        "model_path": "Qwen/Qwen2.5-7B-Instruct-AWQ",
        "tokenizer_path": "Qwen/Qwen2.5-7B-Instruct-AWQ",
        "model_name": "Qwen 2.5 7B (AWQ)",
        "context_size": 32768,
        "quantization": "AWQ",
        "size_gb": 4.2,
        "min_vram_gb": 8,
        "description": "Good balance for consumer GPUs",
        "recommended_for": "Standard desktops, RTX 3060"
    },
    "Qwen/Qwen2.5-14B-Instruct-AWQ": {
        "model_path": "Qwen/Qwen2.5-14B-Instruct-AWQ",
        "tokenizer_path": "Qwen/Qwen2.5-14B-Instruct-AWQ",
        "model_name": "Qwen 2.5 14B (AWQ)",
        "context_size": 32768,
        "quantization": "AWQ",
        "size_gb": 8.5,
        "min_vram_gb": 12,
        "description": "High quality for prosumer GPUs",
        "recommended_for": "RTX 4070, RTX 3090"
    },
    "Qwen/Qwen2.5-32B-Instruct-AWQ": {
        "model_path": "Qwen/Qwen2.5-32B-Instruct-AWQ",
        "tokenizer_path": "Qwen/Qwen2.5-32B-Instruct-AWQ",
        "model_name": "Qwen 2.5 32B (AWQ)",
        "context_size": 32768,
        "quantization": "AWQ",
        "size_gb": 18.0,
        "min_vram_gb": 24,
        "description": "Best quality for 24GB+ GPUs",
        "recommended_for": "RTX 4090, RTX 3090, data center"
    }
}

# Cache directory for models
CACHE_DIR = Path(os.getenv("HF_HOME", "~/.cache/huggingface")).expanduser()


class DownloadRequest(BaseModel):
    model_id: str


class SwitchRequest(BaseModel):
    model_id: str


def normalize_model_config(registry_id: str, info: Dict) -> Dict:
    """
    Normalize model config to new structured format.
    
    Handles both old format (flat dict with "model", "tokenizer", "name")
    and new format (dict with "model_path", "tokenizer_path", "model_name").
    
    Returns a normalized dict with all required fields.
    """
    # Check if this is new format (has model_path)
    if "model_path" in info:
        # New format - ensure all required fields exist
        return {
            "model_path": info.get("model_path", registry_id),
            "tokenizer_path": info.get("tokenizer_path", registry_id),
            "model_name": info.get("model_name", registry_id),
            "context_size": info.get("context_size", 32768),
            "quantization": info.get("quantization"),
            "size_gb": info.get("size_gb", 0.0),
            "min_vram_gb": info.get("min_vram_gb", 0),
            "description": info.get("description", ""),
            "recommended_for": info.get("recommended_for", ""),
        }
    else:
        # Old format - convert to new format
        # Old format had keys like "model", "tokenizer", "name"
        # Map these to new format
        return {
            "model_path": info.get("model", registry_id),
            "tokenizer_path": info.get("tokenizer", info.get("model", registry_id)),
            "model_name": info.get("name", registry_id),
            "context_size": info.get("context_size", 32768),
            "quantization": info.get("quantization"),
            "size_gb": info.get("size_gb", 0.0),
            "min_vram_gb": info.get("min_vram_gb", 0),
            "description": info.get("description", ""),
            "recommended_for": info.get("recommended_for", ""),
        }


def get_downloaded_models() -> List[Dict]:
    """Scan cache directory for downloaded models."""
    models = []
    
    # Check HuggingFace cache
    hub_dir = CACHE_DIR / "hub"
    if hub_dir.exists():
        for model_dir in hub_dir.iterdir():
            if model_dir.is_dir():
                # Extract model name from directory
                model_name = model_dir.name
                # Check if it's a known model
                for registry_id, info in MODEL_REGISTRY.items():
                    if registry_id.replace("/", "--") in model_name:
                        # Calculate size
                        size_bytes = sum(
                            f.stat().st_size for f in model_dir.rglob("*") if f.is_file()
                        )
                        size_gb = size_bytes / (1024**3)
                        
                        models.append({
                            "id": registry_id,
                            "cache_path": str(model_dir),
                            "size_gb": round(size_gb, 1),
                            "status": "ready"
                        })
                        break
    
    return models


def _download_model_task(model_id: str, cache_dir: Path):
    """Background task to download model from HuggingFace Hub."""
    download_status[model_id] = {"status": "downloading", "progress": 0}
    try:
        if not HF_HUB_AVAILABLE:
            download_status[model_id] = {
                "status": "error",
                "error": "huggingface_hub not installed. Install with: pip install huggingface_hub"
            }
            return
        
        # Download the model
        local_path = snapshot_download(
            repo_id=model_id,
            cache_dir=str(cache_dir),
            resume_download=True
        )
        download_status[model_id] = {
            "status": "complete",
            "local_path": local_path
        }
    except Exception as e:
        download_status[model_id] = {
            "status": "error",
            "error": str(e)
        }


@app.get("/api/models/available")
def list_available_models():
    """List models that can be downloaded (normalized to new format)."""
    return {
        "models": [
            normalize_model_config(model_id, info)
            for model_id, info in MODEL_REGISTRY.items()
        ]
    }


@app.get("/api/models/downloaded")
def list_downloaded_models():
    """List models currently in local cache."""
    models = get_downloaded_models()
    return {"models": models, "count": len(models)}


@app.post("/api/models/download")
def download_model(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start downloading a model in the background."""
    model_id = request.model_id

    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found in registry")

    # Check if already downloaded
    downloaded = get_downloaded_models()
    if any(m["id"] == model_id for m in downloaded):
        return {
            "model_id": model_id,
            "status": "already_downloaded",
            "message": "Model is already in cache"
        }

    # Start actual download in background
    background_tasks.add_task(_download_model_task, model_id, CACHE_DIR)

    return {
        "model_id": model_id,
        "status": "download_started",
        "message": f"Downloading {model_id} in background...",
        "check_status": f"GET /api/models/download/{model_id}/status"
    }


@app.get("/api/models/download/{model_id}/status")
def get_download_status(model_id: str):
    """Get the status of a model download."""
    if model_id not in download_status:
        return {"model_id": model_id, "status": "not_found"}
    return {"model_id": model_id, **download_status[model_id]}


@app.post("/api/models/switch")
def switch_model(request: SwitchRequest):
    """Switch the active model and restart vLLM container."""
    model_id = request.model_id
    
    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    # Check if model is downloaded
    downloaded = get_downloaded_models()
    if not any(m["id"] == model_id for m in downloaded):
        raise HTTPException(
            status_code=400, 
            detail=f"Model {model_id} not downloaded. Download first."
        )
    
    # Get current model from vLLM
    current_model = os.getenv("LLM_MODEL", "unknown")
    
    # Actually restart the vLLM container with new model
    # Note: docker update does NOT support -e for env vars. We use docker compose instead.
    try:
        # Find compose file and update LLM_MODEL in .env, then recreate container
        compose_file = None
        for candidate in ["docker-compose.yml", "compose/docker-compose.cluster.yml"]:
            if os.path.exists(candidate):
                compose_file = candidate
                break
        
        if not compose_file:
            raise HTTPException(
                status_code=500,
                detail="Could not find docker-compose.yml"
            )
        
        # Update .env file with new model
        env_file = ".env"
        if os.path.exists(env_file):
            # Read file and detect trailing newline
            with open(env_file, "rb") as f:
                content = f.read()
            
            has_trailing_newline = content.endswith(b"\n") if content else False
            
            # Decode and split into lines (preserves line endings)
            env_lines = content.decode("utf-8").splitlines(keepends=True)
            
            # Replace or add LLM_MODEL
            model_updated = False
            new_lines = []
            for line in env_lines:
                if line.startswith("LLM_MODEL="):
                    new_lines.append(f"LLM_MODEL={model_id}\n")
                    model_updated = True
                else:
                    new_lines.append(line)
            
            if not model_updated:
                new_lines.append(f"LLM_MODEL={model_id}\n")
            
            # Write back with preserved trailing newline behavior
            with open(env_file, "w") as f:
                f.writelines(new_lines)
                # Only add trailing newline if original had one and last line doesn't
                if has_trailing_newline and new_lines and not new_lines[-1].endswith("\n"):
                    f.write("\n")
        
        # Recreate vLLM container with new env
        result = subprocess.run(
            ["docker", "compose", "-f", compose_file, "up", "-d", "--force-recreate", "vllm"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to recreate container: {result.stderr}"
            )
        
        return {
            "success": True,
            "previous_model": current_model,
            "new_model": model_id,
            "message": f"Model switched to {model_id}. vLLM container recreated.",
            "container": "vllm",
            "status": "recreated",
            "compose_file": compose_file
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Container operation timed out")
    except FileNotFoundError:
        # Docker not available (development mode)
        return {
            "success": True,
            "previous_model": current_model,
            "new_model": model_id,
            "message": "Model switch scheduled. Docker not available - manual restart required.",
            "manual_steps": [
                f"Update .env: LLM_MODEL={model_id}",
                f"docker compose up -d --force-recreate vllm"
            ],
            "note": "Docker CLI not found. Run commands manually."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch model: {str(e)}")


@app.delete("/api/models/{model_id:path}")
def delete_model(model_id: str):
    """Delete a model from cache to free space."""
    import re
    
    # Validate model_id against whitelist (MODEL_REGISTRY keys)
    # This prevents path traversal attacks
    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found in registry")
    
    # Sanitize model_id for filesystem use - stricter regex for security
    safe_id = re.sub(r'[^a-zA-Z0-9_\-\.]', '--', model_id)
    
    # Find model in cache
    hub_dir = CACHE_DIR / "hub"
    model_dir = hub_dir / f"models--{safe_id}"
    
    # Security check: ensure resolved path is within cache directory
    try:
        resolved_path = model_dir.resolve()
        resolved_cache = CACHE_DIR.resolve()
        if not str(resolved_path).startswith(str(resolved_cache)):
            raise HTTPException(status_code=400, detail="Invalid model path")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid model path")
    
    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found in cache")

    # Calculate size before deletion
    size_bytes = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
    size_gb = size_bytes / (1024**3)

    # Actually delete the directory
    try:
        shutil.rmtree(model_dir)
        # Also clean up any empty parent directories
        parent = model_dir.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")

    return {
        "model_id": model_id,
        "action": "deleted",
        "space_freed_gb": round(size_gb, 1),
        "message": f"Successfully deleted {model_id}, freed {size_gb:.1f}GB"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "cache_dir": str(CACHE_DIR)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)
