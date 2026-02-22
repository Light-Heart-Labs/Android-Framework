#!/bin/bash
# Dream Server Validation Script
# Run after install to confirm everything is working

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║     🧪 Dream Server Validation Test       ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

PASSED=0
FAILED=0

check() {
    local name="$1"
    local cmd="$2"
    printf "  %-30s " "$name..."
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
    fi
}

echo "1. Container Status"
echo "───────────────────"
check "vLLM running" "docker compose ps vllm 2>/dev/null | grep -q 'Up\|running'"
check "Open WebUI running" "docker compose ps open-webui 2>/dev/null | grep -q 'Up\|running'"

echo ""
echo "2. Health Endpoints"
echo "───────────────────"
check "vLLM health" "curl -sf http://localhost:8000/health"
check "vLLM models" "curl -sf http://localhost:8000/v1/models | grep -q model"
check "WebUI reachable" "curl -sf http://localhost:3000 -o /dev/null"

echo ""
echo "3. Inference Test"
echo "─────────────────"
printf "  %-30s " "Chat completion..."
RESPONSE=$(curl -sf http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "'"$(curl -sf http://localhost:8000/v1/models | jq -r '.data[0].id // "Qwen/Qwen2.5-32B-Instruct-AWQ"')"'",
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 10
    }' 2>/dev/null)

if echo "$RESPONSE" | grep -q "content"; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Check optional services
echo ""
echo "4. Optional Services (if enabled)"
echo "──────────────────────────────────"

if docker compose ps whisper 2>/dev/null | grep -q "Up\|running"; then
    check "Whisper STT" "curl -sf http://localhost:9000/"
else
    printf "  %-30s ${YELLOW}○ SKIP (not enabled)${NC}\n" "Whisper STT..."
fi

if docker compose ps tts 2>/dev/null | grep -q "Up\|running"; then
    check "OpenTTS" "curl -sf http://localhost:8880/api/voices"
else
    printf "  %-30s ${YELLOW}○ SKIP (not enabled)${NC}\n" "OpenTTS..."
fi

if docker compose ps n8n 2>/dev/null | grep -q "Up\|running"; then
    check "n8n workflows" "curl -sf http://localhost:5678/"
else
    printf "  %-30s ${YELLOW}○ SKIP (not enabled)${NC}\n" "n8n workflows..."
fi

if docker compose ps qdrant 2>/dev/null | grep -q "Up\|running"; then
    check "Qdrant vector DB" "curl -sf http://localhost:6333/"
else
    printf "  %-30s ${YELLOW}○ SKIP (not enabled)${NC}\n" "Qdrant vector DB..."
fi

# Summary
echo ""
echo "═══════════════════════════════════════════"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Dream Server is ready! ($PASSED tests passed)${NC}"
    echo ""
    echo "   Open WebUI:  http://localhost:3000"
    echo "   API:         http://localhost:8000/v1/..."
    echo ""
else
    echo -e "${RED}⚠️  $FAILED test(s) failed, $PASSED passed${NC}"
    echo ""
    echo "   Troubleshooting:"
    echo "   - Check logs:  docker compose logs -f"
    echo "   - vLLM logs:   docker compose logs -f vllm"
    echo "   - Restart:     docker compose restart"
    echo ""
    exit 1
fi
