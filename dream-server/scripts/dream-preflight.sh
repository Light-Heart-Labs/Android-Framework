#!/bin/bash
# dream-preflight.sh — Quick health check before first chat
# Usage: ./scripts/dream-preflight.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DREAM_DIR="$(dirname "$SCRIPT_DIR")"
cd "$DREAM_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}Dream Server Preflight Check${NC}"
echo "=============================="
echo ""

# Check Docker is running
echo -n "Docker daemon... "
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓ running${NC}"
else
    echo -e "${RED}✗ not running${NC}"
    echo "  Fix: Start Docker Desktop or run 'sudo systemctl start docker'"
    exit 1
fi

# Check containers are up
echo -n "Core containers... "
if docker compose ps | grep -q "dream-vllm"; then
    echo -e "${GREEN}✓ running${NC}"
else
    echo -e "${RED}✗ not running${NC}"
    echo "  Fix: Run 'docker compose up -d' first"
    exit 1
fi

# Check vLLM health
echo -n "vLLM API (port 8000)... "
if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ healthy${NC}"
else
    echo -e "${YELLOW}⚠ starting up${NC}"
    echo "  The model is still loading. Wait 1-2 minutes and retry."
    echo "  Monitor: docker compose logs -f vllm"
fi

# Check WebUI
echo -n "Open WebUI (port 3000)... "
if curl -sf http://localhost:3000 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ accessible${NC}"
else
    echo -e "${YELLOW}⚠ not ready${NC}"
fi

# Check GPU if available
echo -n "GPU availability... "
if docker exec dream-vllm nvidia-smi >/dev/null 2>&1; then
    GPU_MEM=$(docker exec dream-vllm nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
    echo -e "${GREEN}✓ detected (${GPU_MEM}MB free)${NC}"
else
    echo -e "${YELLOW}⚠ not detected (CPU mode)${NC}"
fi

# Check voice services if enabled
echo -n "Voice services... "
if docker compose ps | grep -q "dream-whisper"; then
    WHISPER_OK=$(curl -sf http://localhost:9000/ >/dev/null 2>&1 && echo "yes" || echo "no")
    TTS_OK=$(curl -sf http://localhost:8880/health >/dev/null 2>&1 && echo "yes" || echo "no")
    if [[ "$WHISPER_OK" == "yes" && "$TTS_OK" == "yes" ]]; then
        echo -e "${GREEN}✓ whisper + TTS ready${NC}"
    else
        echo -e "${YELLOW}⚠ partial (whisper:$WHISPER_OK, tts:$TTS_OK)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ not enabled${NC} (run: docker compose --profile voice up -d)"
fi

echo ""
echo -e "${CYAN}Next steps:${NC}"
echo "  1. Open http://localhost:3000"
echo "  2. Sign in (first user becomes admin)"
echo "  3. Type 'What's 2+2?' to test"
echo ""
echo "Need help? See docs/TROUBLESHOOTING.md"
