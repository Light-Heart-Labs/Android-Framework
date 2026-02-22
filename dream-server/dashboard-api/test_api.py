#!/usr/bin/env python3
"""
Dashboard API Test Script
Quick validation that all endpoints return expected data structures.
"""

import asyncio
import sys

# Allow running without installing
sys.path.insert(0, '.')

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    print("✓ /health")


def test_disk():
    """Test /disk endpoint."""
    response = client.get("/disk")
    assert response.status_code == 200
    data = response.json()
    assert "path" in data
    assert "used_gb" in data
    assert "total_gb" in data
    assert "percent" in data
    print(f"✓ /disk — {data['used_gb']:.1f}/{data['total_gb']:.1f} GB ({data['percent']}%)")


def test_bootstrap():
    """Test /bootstrap endpoint."""
    response = client.get("/bootstrap")
    assert response.status_code == 200
    data = response.json()
    assert "active" in data
    status = "downloading" if data["active"] else "idle"
    print(f"✓ /bootstrap — {status}")


def test_gpu():
    """Test /gpu endpoint (may fail without GPU)."""
    response = client.get("/gpu")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ /gpu — {data['name']}: {data['memory_used_mb']}/{data['memory_total_mb']} MB")
    else:
        print(f"⚠ /gpu — not available (expected on non-GPU systems)")


def test_services():
    """Test /services endpoint."""
    response = client.get("/services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    healthy = sum(1 for s in data if s["status"] == "healthy")
    print(f"✓ /services — {healthy}/{len(data)} healthy")


def test_status():
    """Test /status endpoint (full system status)."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "services" in data
    assert "disk" in data
    assert "bootstrap" in data
    print(f"✓ /status — full system status returned")


def main():
    print("=" * 50)
    print("Dashboard API Tests")
    print("=" * 50)
    
    try:
        test_health()
        test_disk()
        test_bootstrap()
        test_gpu()
        test_services()
        test_status()
        print("=" * 50)
        print("All tests passed! ✓")
        return 0
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
