#!/bin/bash
# Deploy Voice Agent connecting to cluster services
#
# Usage: bash scripts/deploy-voice-agent.sh
#
# Note: Update LIVEKIT_URL, STT_URL, TTS_URL, LLM_URL env vars if not running locally.

set -e

# Cluster service URLs (adjust if running elsewhere)
# Default: local deployment on .122 - update LIVEKIT_URL for remote setups
LIVEKIT_URL=${LIVEKIT_URL:-ws://localhost:7880}
if [[ -z "${LIVEKIT_API_KEY}" ]]; then
    echo "Error: LIVEKIT_API_KEY not set" >&2
    exit 1
fi
if [[ -z "${LIVEKIT_API_SECRET}" ]]; then
    echo "Error: LIVEKIT_API_SECRET not set" >&2
    exit 1
fi
STT_URL=${STT_URL:-http://localhost:9101}
TTS_URL=${TTS_URL:-http://localhost:9102}
LLM_URL=${LLM_URL:-http://localhost:9100/v1}
LLM_MODEL=${LLM_MODEL:-Qwen/Qwen2.5-32B-Instruct-AWQ}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="${SCRIPT_DIR}/../agents/voice"

echo "🎤 Deploying Voice Agent..."
echo "  LiveKit: ${LIVEKIT_URL}"
echo "  STT: ${STT_URL}"
echo "  TTS: ${TTS_URL}"
echo "  LLM: ${LLM_URL}"
echo ""

# Stop existing if running
docker stop dream-voice-agent 2>/dev/null || true
docker rm dream-voice-agent 2>/dev/null || true

# Build the agent
echo "Building voice agent..."
docker build -t dream-voice-agent:latest "${AGENT_DIR}"

# Run the agent
docker run -d \
  --name dream-voice-agent \
  --restart unless-stopped \
  --network host \
  -e LIVEKIT_URL="${LIVEKIT_URL}" \
  -e LIVEKIT_API_KEY="${LIVEKIT_API_KEY}" \
  -e LIVEKIT_API_SECRET="${LIVEKIT_API_SECRET}" \
  -e STT_URL="${STT_URL}" \
  -e TTS_URL="${TTS_URL}" \
  -e LLM_URL="${LLM_URL}" \
  -e LLM_MODEL="${LLM_MODEL}" \
  dream-voice-agent:latest

# Wait for container to start and check health
echo "Waiting for agent to initialize..."
sleep 3
if docker ps | grep -q dream-voice-agent; then
    echo "✅ Voice Agent started successfully"
else
    echo "⚠️  Voice Agent container failed to start - check logs: docker logs dream-voice-agent"
    exit 1
fi

echo ""
echo "✅ Voice Agent deployed!"
echo ""
echo "The agent will automatically connect to LiveKit and handle:"
echo "  - Speech-to-text via Whisper"
echo "  - LLM responses via vLLM"
echo "  - Text-to-speech via Kokoro"
echo ""
echo "To test: Open the Dream Server dashboard → Voice page"
echo "Logs: docker logs -f dream-voice-agent"
