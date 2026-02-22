#!/bin/bash
# Entrypoint script for Dream Server Voice Agent - Offline Mode
# M1 Phase 2 - Zero cloud dependencies

set -e

echo "=== Dream Server Voice Agent (Offline Mode) ==="
echo "Starting at $(date)"

# Environment validation
if [[ -z "${LIVEKIT_URL}" ]]; then
    echo "ERROR: LIVEKIT_URL not set"
    exit 1
fi

if [[ -z "${LIVEKIT_API_KEY}" ]]; then
    echo "ERROR: LIVEKIT_API_KEY not set"
    exit 1
fi

if [[ -z "${LIVEKIT_API_SECRET}" ]]; then
    echo "ERROR: LIVEKIT_API_SECRET not set"
    exit 1
fi

# Health check dependencies
echo "=== Health Check Dependencies ==="
for service in vllm whisper tts; do
    # Map service names to environment variable names
    case "$service" in
        vllm) url_var="LLM_URL" ;;
        whisper) url_var="STT_URL" ;;
        tts) url_var="TTS_URL" ;;
    esac
    url="${!url_var}"
    if [[ -n "$url" ]]; then
        echo "Checking $service at $url..."
        if [[ "$service" == "vllm" ]]; then
            curl -f "${url}/health" || echo "WARNING: vLLM health check failed"
        elif [[ "$service" == "whisper" ]]; then
            curl -f "${url}/" || echo "WARNING: Whisper health check failed"
        elif [[ "$service" == "tts" ]]; then
            curl -f "${url}/health" || echo "WARNING: TTS health check failed"
        fi
    fi
done

# Set default values
export LLM_MODEL=${LLM_MODEL:-"Qwen/Qwen2.5-32B-Instruct-AWQ"}
export STT_MODEL=${STT_MODEL:-"base"}
export TTS_VOICE=${TTS_VOICE:-"af_heart"}
export DETERMINISTIC_ENABLED=${DETERMINISTIC_ENABLED:-"true"}
export DETERMINISTIC_THRESHOLD=${DETERMINISTIC_THRESHOLD:-"0.85"}
export OFFLINE_MODE=${OFFLINE_MODE:-"true"}

echo "=== Configuration ==="
echo "LLM Model: ${LLM_MODEL}"
echo "STT Model: ${STT_MODEL}"
echo "TTS Voice: ${TTS_VOICE}"
echo "Deterministic Flows: ${DETERMINISTIC_ENABLED}"
echo "Offline Mode: ${OFFLINE_MODE}"

# Start health check server in background
echo "Starting health check server..."
python health_check.py &
HEALTH_PID=$!

# Start the main agent
echo "Starting voice agent..."
exec python agent.py