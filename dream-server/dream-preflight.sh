#!/bin/bash
# Dream Server Pre-flight Check
# Validates all services start correctly before user interaction
# Usage: ./dream-preflight.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DREAM_DIR="$SCRIPT_DIR"
LOG_FILE="$DREAM_DIR/preflight-$(date +%Y%m%d-%H%M%S).log"

# Load SERVICE_HOST from .env if available, default to localhost
if [ -f "$DREAM_DIR/.env" ]; then
    # shellcheck source=/dev/null
    source "$DREAM_DIR/.env" 2>/dev/null || true
fi
SERVICE_HOST="${SERVICE_HOST:-localhost}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

log() {
    echo -e "$1"
    echo -e "$1" | sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"
}
pass() { log "${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
fail() { log "${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }
warn() { log "${YELLOW}⚠${NC} $1"; WARN=$((WARN+1)); }

echo "" > "$LOG_FILE"
log "========================================"
log "Dream Server Pre-flight Check"
log "Started: $(date)"
log "========================================"
log ""

# 1. Docker check
log "[1/8] Checking Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    pass "Docker installed: $DOCKER_VERSION"
    
    if docker info &> /dev/null; then
        pass "Docker daemon running"
    else
        fail "Docker daemon not running — start with: sudo systemctl start docker"
    fi
else
    fail "Docker not installed"
fi
log ""

# 2. Docker Compose check
log "[2/8] Checking Docker Compose..."
if docker compose version &> /dev/null 2>&1 || docker-compose version &> /dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version 2>/dev/null | awk '{print $4}' || docker-compose version 2>/dev/null | head -1 | awk '{print $3}')
    pass "Docker Compose available: $COMPOSE_VERSION"
else
    fail "Docker Compose not found"
fi
log ""

# 3. GPU check
log "[3/8] Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=""
    if raw_gpu=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null); then
        GPU_INFO=$(echo "$raw_gpu" | head -1)
    fi
    if [ -n "$GPU_INFO" ]; then
        pass "NVIDIA GPU detected: $GPU_INFO"
        
        # Check if nvidia-docker runtime is available
        if docker info 2>/dev/null | grep -q "nvidia"; then
            pass "NVIDIA Docker runtime available"
        else
            warn "NVIDIA Docker runtime not configured — GPU containers may fail"
        fi
    else
        warn "nvidia-smi found but no GPU detected"
    fi
else
    warn "nvidia-smi not found — GPU features will be unavailable"
fi
log ""

# 4. LLM Endpoint check
log "[4/8] Checking LLM endpoint..."
LLM_ENDPOINTS=("http://${SERVICE_HOST}:8000" "http://localhost:8000" "http://127.0.0.1:8000")
LLM_FOUND=false

for ENDPOINT in "${LLM_ENDPOINTS[@]}"; do
    if curl -s "$ENDPOINT/health" &> /dev/null || curl -s "$ENDPOINT/v1/models" &> /dev/null; then
        pass "LLM endpoint responding at $ENDPOINT"
        LLM_FOUND=true
        break
    fi
done

if [ "$LLM_FOUND" = false ]; then
    fail "No LLM endpoint found — checked: ${LLM_ENDPOINTS[*]}"
    warn "Start vLLM with: docker compose up -d vllm"
fi
log ""

# 5. Whisper STT check
log "[5/8] Checking Whisper STT..."
WHISPER_ENDPOINTS=("http://${SERVICE_HOST}:9000" "http://localhost:9000" "http://127.0.0.1:9000")
WHISPER_FOUND=false

for ENDPOINT in "${WHISPER_ENDPOINTS[@]}"; do
    if curl -s "$ENDPOINT/health" &> /dev/null || curl -s -X POST "$ENDPOINT/transcribe" -H "Content-Type: application/json" -d '{"audio":""}' &> /dev/null; then
        pass "Whisper STT responding at $ENDPOINT"
        WHISPER_FOUND=true
        break
    fi
done

if [ "$WHISPER_FOUND" = false ]; then
    warn "Whisper STT not found — voice input will be unavailable"
fi
log ""

# 6. TTS check
log "[6/8] Checking TTS (Kokoro)..."
TTS_ENDPOINTS=("http://${SERVICE_HOST}:8880" "http://localhost:8880" "http://127.0.0.1:8880")
TTS_FOUND=false

for ENDPOINT in "${TTS_ENDPOINTS[@]}"; do
    if curl -s "$ENDPOINT/health" &> /dev/null; then
        pass "TTS endpoint responding at $ENDPOINT"
        TTS_FOUND=true
        break
    fi
done

if [ "$TTS_FOUND" = false ]; then
    warn "TTS not found — voice output will be unavailable"
fi
log ""

# 7. Embeddings check
log "[7/8] Checking Embeddings..."
EMBEDDING_ENDPOINTS=("http://${SERVICE_HOST}:8090" "http://localhost:8090" "http://127.0.0.1:8090")
EMBEDDING_FOUND=false

for ENDPOINT in "${EMBEDDING_ENDPOINTS[@]}"; do
    if curl -s "$ENDPOINT/health" &> /dev/null; then
        pass "Embeddings endpoint responding at $ENDPOINT"
        EMBEDDING_FOUND=true
        break
    fi
done

if [ "$EMBEDDING_FOUND" = false ]; then
    warn "Embeddings not found — RAG features will be unavailable"
fi
log ""

# 8. LiveKit check
log "[8/8] Checking LiveKit..."
LIVEKIT_ENDPOINTS=("http://${SERVICE_HOST}:7880" "http://localhost:7880" "http://127.0.0.1:7880")
LIVEKIT_FOUND=false

for ENDPOINT in "${LIVEKIT_ENDPOINTS[@]}"; do
    if curl -s "$ENDPOINT" &> /dev/null; then
        pass "LiveKit responding at $ENDPOINT"
        LIVEKIT_FOUND=true
        break
    fi
done

if [ "$LIVEKIT_FOUND" = false ]; then
    warn "LiveKit not found — voice agent features will be unavailable"
fi
log ""

# Summary
log "========================================"
log "Pre-flight Summary"
log "========================================"
log "$(printf "${GREEN}✓${NC} Passed: %d" "$PASS")"
log "$(printf "${RED}✗${NC} Failed: %d" "$FAIL")"
log "$(printf "${YELLOW}⚠${NC} Warnings: %d" "$WARN")"
log ""

if [ $FAIL -eq 0 ]; then
    pass "Pre-flight PASSED — Dream Server is ready!"
    EXIT_CODE=0
else
    fail "Pre-flight FAILED — fix issues above before proceeding"
    EXIT_CODE=1
fi

log ""
log "Full log: $LOG_FILE"

exit $EXIT_CODE
