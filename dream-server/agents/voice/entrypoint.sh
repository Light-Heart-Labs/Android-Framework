#!/bin/bash
# Voice Agent Entrypoint
set -euo pipefail

echo "========================================"
echo "  Dream Server Voice Agent"
echo "========================================"
echo ""
echo "Configuration:"
echo "  LLM URL: ${LLM_URL:-http://vllm:8000/v1}"
echo "  STT URL: ${STT_URL:-http://localhost:9000}"
echo "  TTS URL: ${TTS_URL:-http://localhost:8880}"
echo ""

# Health check function
wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    echo "Waiting for $name at $url..."
    while [ $attempt -le $max_attempts ]; do
        if curl -sf --connect-timeout 10 --max-time 30 "$url" > /dev/null 2>&1; then
            echo "✓ $name is ready"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts - $name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "✗ $name failed to respond after $max_attempts attempts"
    return 1
}

# Wait for required services
echo "Checking service dependencies..."
# Extract base URL for health check (remove /v1 suffix)
LLM_BASE_URL="${LLM_URL:-http://vllm:8000/v1}"
LLM_BASE_URL="${LLM_BASE_URL%/v1}"
# vLLM uses /v1/models as health indicator, not /health
wait_for_service "LLM (vLLM)" "${LLM_BASE_URL}/v1/models" 60 || echo "Warning: LLM health check failed, continuing anyway..."
STT_BASE_URL="${STT_URL:-http://whisper:9000/v1}"
STT_BASE_URL="${STT_BASE_URL%/v1}"
# Whisper health check - try /health or just check if port is open
wait_for_service "STT (Whisper)" "${STT_BASE_URL}/" 10 || echo "Warning: STT health check failed, continuing anyway..."

# TTS is optional for some configs
if [ -n "${TTS_URL:-}" ]; then
    # Extract base URL for health check (remove /v1 suffix if present)
    TTS_BASE_URL="${TTS_URL%/v1}"
    wait_for_service "TTS" "${TTS_BASE_URL}/health" 5 || echo "Warning: TTS not available, continuing anyway..."
fi

echo ""
echo "All services ready. Starting voice agent..."
echo ""

# Start the voice agent
exec python agent.py start
