#!/bin/bash
# Dream Server Status Check
# Quick health check for all services

set -e

INSTALL_DIR="${INSTALL_DIR:-$HOME/dream-server}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Dream Server Status${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Source .env for port variables
source "$INSTALL_DIR/.env" 2>/dev/null || true

check_service() {
    local name=$1
    local url=$2
    local port_var=$3
    local port_value="${!port_var:-$3}"
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $name (port $port_value)"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name (port $port_value) - not responding"
        return 1
    fi
}

echo -e "${CYAN}Services:${NC}"
check_service "Open WebUI" "http://localhost:${WEBUI_PORT:-3000}" "WEBUI_PORT" || true
check_service "n8n" "http://localhost:${N8N_PORT:-5678}" "N8N_PORT" || true
check_service "vLLM" "http://localhost:${VLLM_PORT:-8000}/health" "VLLM_PORT" || true
check_service "Qdrant" "http://localhost:${QDRANT_PORT:-6333}" "QDRANT_PORT" || true
check_service "Whisper" "http://localhost:${WHISPER_PORT:-9000}" "WHISPER_PORT" || true
check_service "TTS (Kokoro)" "http://localhost:${TTS_PORT:-8880}" "TTS_PORT" || true
check_service "Embeddings" "http://localhost:${EMBEDDINGS_PORT:-8090}" "EMBEDDINGS_PORT" || true

echo ""
echo -e "${CYAN}Containers:${NC}"
cd "$INSTALL_DIR" 2>/dev/null && docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  Could not check containers"

echo ""
if command -v nvidia-smi &> /dev/null; then
    echo -e "${CYAN}GPU:${NC}"
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader 2>/dev/null | while read line; do
        echo "  $line"
    done
fi

echo ""
echo -e "${CYAN}Disk Usage:${NC}"
if [ -d "$INSTALL_DIR" ]; then
    du -sh "$INSTALL_DIR"/* 2>/dev/null | head -10
else
    echo "  Install directory not found: $INSTALL_DIR"
fi

echo ""
