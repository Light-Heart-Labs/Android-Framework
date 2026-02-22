#!/usr/bin/env python3
"""
Universal health check script for Dream Server offline mode.
Works across all container images (no curl/wget dependency).
"""

import sys
import urllib.request
import urllib.error
import socket

def check_http(url, timeout=5):
    """Check HTTP endpoint returns 200."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout):
        return False

def check_tcp(host, port, timeout=5):
    """Check TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: healthcheck.py <url|host:port>")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if target.startswith('http://') or target.startswith('https://'):
        ok = check_http(target)
    elif ':' in target:
        host, port = target.rsplit(':', 1)
        ok = check_tcp(host, int(port))
    else:
        print(f"Invalid target: {target}")
        sys.exit(1)
    
    sys.exit(0 if ok else 1)
