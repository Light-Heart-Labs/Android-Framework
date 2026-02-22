#!/usr/bin/env python3
"""
Dream Server API Endpoint Tests
Run with: pytest test_endpoints.py -v
"""

import pytest
import httpx
import asyncio
import os
from typing import Optional

# Service URLs (allow environment overrides)
API_URL = os.getenv("DREAM_API_URL", "http://localhost:3002")
VLLM_URL = os.getenv("DREAM_VLLM_URL", "http://localhost:8000")
N8N_URL = os.getenv("DREAM_N8N_URL", "http://localhost:5678")


@pytest.fixture
def client():
    return httpx.Client(timeout=10.0)


class TestDashboardAPI:
    """Dashboard API endpoint tests."""
    
    def test_health(self, client):
        """API health check returns ok."""
        r = client.get(f"{API_URL}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
    
    def test_api_status(self, client):
        """Full status endpoint returns expected structure."""
        r = client.get(f"{API_URL}/api/status")
        assert r.status_code == 200
        data = r.json()
        assert "gpu" in data or "services" in data
        assert "tier" in data
    
    def test_gpu_metrics(self, client):
        """GPU endpoint returns NVIDIA metrics."""
        r = client.get(f"{API_URL}/gpu")
        if r.status_code == 503:
            pytest.skip("No GPU available")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert "memory_used_mb" in data
        assert "memory_total_mb" in data
    
    def test_services_list(self, client):
        """Services endpoint returns service health."""
        r = client.get(f"{API_URL}/services")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Each service should have id, name, status
        for svc in data:
            assert "id" in svc
            assert "name" in svc
            assert "status" in svc
    
    def test_disk_usage(self, client):
        """Disk endpoint returns usage info."""
        r = client.get(f"{API_URL}/disk")
        assert r.status_code == 200
        data = r.json()
        assert "path" in data
        assert "used_gb" in data
        assert "total_gb" in data


class TestModelAPI:
    """Model Manager API tests."""
    
    def test_model_catalog(self, client):
        """Model catalog returns list of models."""
        r = client.get(f"{API_URL}/api/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert len(data["models"]) > 0
        # Each model should have required fields
        for model in data["models"]:
            assert "id" in model
            assert "name" in model
            assert "vramRequired" in model
            assert "status" in model
    
    def test_model_vram_info(self, client):
        """Model catalog includes GPU VRAM info."""
        r = client.get(f"{API_URL}/api/models")
        assert r.status_code == 200
        data = r.json()
        assert "gpu" in data
        assert "vramTotal" in data["gpu"]


class TestWorkflowAPI:
    """Workflow Gallery API tests."""
    
    def test_workflow_catalog(self, client):
        """Workflow catalog returns list of workflows."""
        r = client.get(f"{API_URL}/api/workflows")
        assert r.status_code == 200
        data = r.json()
        assert "workflows" in data
        assert len(data["workflows"]) > 0
    
    def test_workflow_structure(self, client):
        """Each workflow has required fields."""
        r = client.get(f"{API_URL}/api/workflows")
        assert r.status_code == 200
        data = r.json()
        for wf in data["workflows"]:
            assert "id" in wf
            assert "name" in wf
            assert "description" in wf
            assert "dependencies" in wf
            assert "status" in wf
    
    def test_workflow_categories(self, client):
        """Workflow catalog includes categories."""
        r = client.get(f"{API_URL}/api/workflows")
        assert r.status_code == 200
        data = r.json()
        assert "categories" in data
        assert len(data["categories"]) > 0


class TestVoiceAPI:
    """Voice API tests."""
    
    def test_voice_status(self, client):
        """Voice status returns service health."""
        r = client.get(f"{API_URL}/api/voice/status")
        assert r.status_code == 200
        data = r.json()
        assert "services" in data
        assert "stt" in data["services"]
        assert "tts" in data["services"]
        assert "livekit" in data["services"]


class TestVLLM:
    """vLLM inference tests."""
    
    def test_vllm_health(self, client):
        """vLLM health check."""
        try:
            r = client.get(f"{VLLM_URL}/health")
            assert r.status_code == 200
        except httpx.ConnectError:
            pytest.skip("vLLM not running")
    
    def test_vllm_inference(self, client):
        """vLLM can generate completions."""
        try:
            r = client.post(
                f"{VLLM_URL}/v1/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
                    "messages": [{"role": "user", "content": "Say hello"}],
                    "max_tokens": 10,
                    "stream": False
                },
                timeout=30.0
            )
            if r.status_code == 200:
                data = r.json()
                assert "choices" in data
                assert len(data["choices"]) > 0
                assert "message" in data["choices"][0]
        except httpx.ConnectError:
            pytest.skip("vLLM not running")


class TestN8N:
    """n8n workflow engine tests."""
    
    def test_n8n_health(self, client):
        """n8n health check."""
        try:
            r = client.get(f"{N8N_URL}/healthz")
            assert r.status_code == 200
        except httpx.ConnectError:
            pytest.skip("n8n not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
