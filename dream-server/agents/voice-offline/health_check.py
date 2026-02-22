#!/usr/bin/env python3
"""
Health check server for Dream Server Voice Agent - Offline Mode
Simple HTTP server for container health checks
"""

import http.server
import socketserver
import json
import os
import requests
import threading
from datetime import datetime, timezone

class HealthHandler(http.server.BaseHTTPRequestHandler):
    """Health check handler - only serves /health endpoint, no file serving"""
    
    def log_message(self, format, *args):
        """Suppress default request logging"""
        pass
    
    def do_GET(self):
        if self.path == '/health':
            self.send_health_check()
        else:
            self.send_error(404, "Not Found")
    
    def send_health_check(self):
        """Perform health check on all dependencies"""
        checks = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0-offline",
            "checks": {}
        }
        
        # Check local services
        services = {
            "vllm": {
                "url": os.getenv("LLM_URL", "http://vllm:8000/v1").removesuffix("/v1").removesuffix("/") + "/health",
                "timeout": 5
            },
            "whisper": {
                "url": os.getenv("STT_URL", "http://whisper:9000/v1").removesuffix("/v1").removesuffix("/") + "/health",
                "timeout": 5
            },
            "tts": {
                "url": os.getenv("TTS_URL", "http://tts:8880/v1").removesuffix("/v1").removesuffix("/") + "/health",
                "timeout": 5
            }
        }
        
        all_healthy = True
        
        for service, config in services.items():
            try:
                response = requests.get(config["url"], timeout=config["timeout"])
                if response.status_code == 200:
                    checks["checks"][service] = {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    checks["checks"][service] = {
                        "status": "unhealthy",
                        "status_code": response.status_code
                    }
                    all_healthy = False
            except Exception as e:
                checks["checks"][service] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                all_healthy = False
        
        if not all_healthy:
            checks["status"] = "unhealthy"
        
        # Check LiveKit credentials
        if not os.getenv("LIVEKIT_API_SECRET"):
            checks["checks"]["livekit"] = {
                "status": "unhealthy",
                "error": "LIVEKIT_API_SECRET not set"
            }
            checks["status"] = "unhealthy"
        else:
            checks["checks"]["livekit"] = {"status": "healthy"}
        
        self.send_response(200 if all_healthy else 503)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(checks, indent=2).encode())

def start_health_server():
    """Start health check server"""
    port = 8080
    with socketserver.TCPServer(("", port), HealthHandler) as httpd:
        print(f"Health check server started on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    start_health_server()