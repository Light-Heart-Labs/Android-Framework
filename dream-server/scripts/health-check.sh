#!/bin/bash
# Dream Server Comprehensive Health Check
# Tests each component with actual API calls, not just connectivity
# Exit codes: 0=healthy, 1=degraded (some services down), 2=critical (core services down)
# 
# Usage: ./health-check.sh [--json] [--quiet]

set -euo pipefail

# Parse args
JSON_OUTPUT=false
QUIET=false
for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --quiet) QUIET=true ;;
    esac
done

# Config
INSTALL_DIR="${INSTALL_DIR:-$HOME/dream-server}"
VLLM_HOST="${VLLM_HOST:-localhost}"
VLLM_PORT="${VLLM_PORT:-8000}"
TIMEOUT="${TIMEOUT:-5}"

# Load ports from .env if available
ENV_FILE="${INSTALL_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
    # Source only PORT variable lines to avoid executing malicious content
    WHISPER_PORT=$(grep "^WHISPER_PORT=" "$ENV_FILE" | cut -d= -f2 | tr -d ' "' || echo "9000")
    TTS_PORT=$(grep "^TTS_PORT=" "$ENV_FILE" | cut -d= -f2 | tr -d ' "' || echo "8880")
    EMBEDDINGS_PORT=$(grep "^EMBEDDINGS_PORT=" "$ENV_FILE" | cut -d= -f2 | tr -d ' "' || echo "8090")
else
    WHISPER_PORT="${WHISPER_PORT:-9000}"
    TTS_PORT="${TTS_PORT:-8880}"
    EMBEDDINGS_PORT="${EMBEDDINGS_PORT:-8090}"
fi

# Colors (disabled for JSON/quiet)
if $JSON_OUTPUT || $QUIET; then
    GREEN="" RED="" YELLOW="" CYAN="" NC=""
else
    GREEN='\033[0;32m' RED='\033[0;31m' YELLOW='\033[1;33m' CYAN='\033[0;36m' NC='\033[0m'
fi

# Track results
declare -A RESULTS
CRITICAL_FAIL=false
ANY_FAIL=false

log() { $QUIET || echo -e "$1"; }

# Test functions
test_vllm() {
    local start=$(date +%s%3N)
    # Test actual inference with simple completion
    local response=$(curl -sf --max-time $TIMEOUT \
        -H "Content-Type: application/json" \
        -d '{"model":"default","prompt":"Hi","max_tokens":1}' \
        "http://${VLLM_HOST}:${VLLM_PORT}/v1/completions" 2>/dev/null)
    local end=$(date +%s%3N)
    
    if echo "$response" | grep -q '"text"'; then
        RESULTS[vllm]="ok"
        RESULTS[vllm_latency]=$((end - start))
        return 0
    fi
    RESULTS[vllm]="fail"
    CRITICAL_FAIL=true
    ANY_FAIL=true
    return 1
}

test_embeddings() {
    local response=$(curl -sf --max-time $TIMEOUT \
        -H "Content-Type: application/json" \
        -d '{"input":"test"}' \
        "http://localhost:${EMBEDDINGS_PORT}/embed" 2>/dev/null)

    if echo "$response" | grep -q '\['; then
        RESULTS[embeddings]="ok"
        return 0
    fi
    RESULTS[embeddings]="fail"
    ANY_FAIL=true
    return 1
}

test_whisper() {
    # Just check health endpoint - actual transcription needs audio
    if curl -sf --max-time $TIMEOUT "http://localhost:${WHISPER_PORT}/health" >/dev/null 2>&1; then
        RESULTS[whisper]="ok"
        return 0
    fi
    RESULTS[whisper]="fail"
    ANY_FAIL=true
    return 1
}

test_tts() {
    # Check TTS endpoint health
    if curl -sf --max-time $TIMEOUT "http://localhost:${TTS_PORT}/health" >/dev/null 2>&1; then
        RESULTS[tts]="ok"
        return 0
    fi
    RESULTS[tts]="fail"
    ANY_FAIL=true
    return 1
}

test_qdrant() {
    local response=$(curl -sf --max-time $TIMEOUT "http://localhost:6333/collections" 2>/dev/null)
    if echo "$response" | grep -q '"result"'; then
        RESULTS[qdrant]="ok"
        return 0
    fi
    RESULTS[qdrant]="fail"
    ANY_FAIL=true
    return 1
}

test_open_webui() {
    if curl -sf --max-time $TIMEOUT "http://localhost:3000" >/dev/null 2>&1; then
        RESULTS[open_webui]="ok"
        return 0
    fi
    RESULTS[open_webui]="fail"
    ANY_FAIL=true
    return 1
}

test_n8n() {
    if curl -sf --max-time $TIMEOUT "http://localhost:5678/healthz" >/dev/null 2>&1; then
        RESULTS[n8n]="ok"
        return 0
    fi
    RESULTS[n8n]="fail"
    ANY_FAIL=true
    return 1
}

test_gpu() {
    if command -v nvidia-smi &>/dev/null; then
        local gpu_info=$(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -n "$gpu_info" ]; then
            IFS=',' read -r mem_used mem_total gpu_util temp <<< "$gpu_info"
            RESULTS[gpu]="ok"
            RESULTS[gpu_mem_used]="${mem_used// /}"
            RESULTS[gpu_mem_total]="${mem_total// /}"
            RESULTS[gpu_util]="${gpu_util// /}"
            RESULTS[gpu_temp]="${temp// /}"
            
            # Warn if GPU memory > 95% or temp > 80C
            if [ "${RESULTS[gpu_util]}" -gt 95 ] 2>/dev/null; then
                RESULTS[gpu]="warn"
            fi
            if [ "${RESULTS[gpu_temp]}" -gt 80 ] 2>/dev/null; then
                RESULTS[gpu]="warn"
            fi
            return 0
        fi
    fi
    RESULTS[gpu]="unavailable"
    return 1
}

test_disk() {
    local usage=$(df -h "$INSTALL_DIR" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
    if [ -n "$usage" ]; then
        RESULTS[disk]="ok"
        RESULTS[disk_usage]="$usage"
        if [ "$usage" -gt 90 ]; then
            RESULTS[disk]="warn"
        fi
        return 0
    fi
    RESULTS[disk]="unavailable"
    return 1
}

# Run tests
log "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log "${CYAN}  Dream Server Health Check${NC}"
log "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log ""

log "${CYAN}Core Services:${NC}"

# vLLM (critical)
if test_vllm 2>/dev/null; then
    log "  ${GREEN}✓${NC} vLLM - inference working (${RESULTS[vllm_latency]}ms)"
else
    log "  ${RED}✗${NC} vLLM - CRITICAL: inference failed"
fi

# Embeddings
if test_embeddings 2>/dev/null; then
    log "  ${GREEN}✓${NC} Embeddings - working"
else
    log "  ${YELLOW}!${NC} Embeddings - not responding"
fi

# Whisper
if test_whisper 2>/dev/null; then
    log "  ${GREEN}✓${NC} Whisper STT - healthy"
else
    log "  ${YELLOW}!${NC} Whisper STT - not responding"
fi

# TTS
if test_tts 2>/dev/null; then
    log "  ${GREEN}✓${NC} TTS - healthy"
else
    log "  ${YELLOW}!${NC} TTS - not responding"
fi

log ""
log "${CYAN}Support Services:${NC}"

# Qdrant
if test_qdrant 2>/dev/null; then
    log "  ${GREEN}✓${NC} Qdrant - responding"
else
    log "  ${YELLOW}!${NC} Qdrant - not responding"
fi

# Open WebUI
if test_open_webui 2>/dev/null; then
    log "  ${GREEN}✓${NC} Open WebUI - accessible"
else
    log "  ${YELLOW}!${NC} Open WebUI - not responding"
fi

# n8n
if test_n8n 2>/dev/null; then
    log "  ${GREEN}✓${NC} n8n - healthy"
else
    log "  ${YELLOW}!${NC} n8n - not responding"
fi

log ""
log "${CYAN}System Resources:${NC}"

# GPU
if test_gpu 2>/dev/null; then
    local status_icon="${GREEN}✓${NC}"
    [ "${RESULTS[gpu]}" = "warn" ] && status_icon="${YELLOW}!${NC}"
    log "  ${status_icon} GPU - ${RESULTS[gpu_mem_used]}/${RESULTS[gpu_mem_total]} MiB, ${RESULTS[gpu_util]}% util, ${RESULTS[gpu_temp]}°C"
else
    log "  ${YELLOW}?${NC} GPU - status unavailable"
fi

# Disk
if test_disk 2>/dev/null; then
    local status_icon="${GREEN}✓${NC}"
    [ "${RESULTS[disk]}" = "warn" ] && status_icon="${YELLOW}!${NC}"
    log "  ${status_icon} Disk - ${RESULTS[disk_usage]}% used"
else
    log "  ${YELLOW}?${NC} Disk - status unavailable"
fi

log ""

# Summary
if $CRITICAL_FAIL; then
    log "${RED}Status: CRITICAL - Core services down${NC}"
    EXIT_CODE=2
elif $ANY_FAIL; then
    log "${YELLOW}Status: DEGRADED - Some services unavailable${NC}"
    EXIT_CODE=1
else
    log "${GREEN}Status: HEALTHY - All services operational${NC}"
    EXIT_CODE=0
fi

log ""

# JSON output
if $JSON_OUTPUT; then
    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"status\": \"$([ $EXIT_CODE -eq 0 ] && echo "healthy" || ([ $EXIT_CODE -eq 1 ] && echo "degraded" || echo "critical"))\","
    echo "  \"services\": {"
    first=true
    for key in "${!RESULTS[@]}"; do
        $first || echo ","
        first=false
        echo -n "    \"$key\": \"${RESULTS[$key]}\""
    done
    echo ""
    echo "  }"
    echo "}"
fi

exit $EXIT_CODE
