#!/bin/bash
# Deploy LiveKit server for voice chat testing
# Usage: bash scripts/deploy-livekit.sh
#
# ⚠️  SECURITY WARNING
# ====================
# Do NOT use default credentials in production or shared environments.
# For production deployments, set LIVEKIT_API_KEY and LIVEKIT_API_SECRET 
# explicitly via environment.

set -e

# Required environment variables
if [[ -z "${LIVEKIT_API_KEY}" ]]; then
    echo "ERROR: LIVEKIT_API_KEY must be set" >&2
    exit 1
fi

if [[ -z "${LIVEKIT_API_SECRET}" ]]; then
    echo "ERROR: LIVEKIT_API_SECRET must be set" >&2
    exit 1
fi

LIVEKIT_PORT=${LIVEKIT_PORT:-7880}
LIVEKIT_RTC_START=${LIVEKIT_RTC_START:-50000}
LIVEKIT_RTC_END=${LIVEKIT_RTC_END:-50100}

# Validate RTC port range
if [[ ${LIVEKIT_RTC_START} -ge ${LIVEKIT_RTC_END} ]]; then
    echo "Error: RTC_START (${LIVEKIT_RTC_START}) must be less than RTC_END (${LIVEKIT_RTC_END})" >&2
    exit 1
fi
if [[ ${LIVEKIT_RTC_START} -lt 1 || ${LIVEKIT_RTC_END} -gt 65535 ]]; then
    echo "Error: RTC ports must be between 1 and 65535" >&2
    exit 1
fi

echo "🎤 Deploying LiveKit server..."

# Create config directory
mkdir -p ~/livekit-config

# Write config
cat > ~/livekit-config/livekit.yaml << YAML
port: ${LIVEKIT_PORT}
rtc:
  port_range_start: ${LIVEKIT_RTC_START}
  port_range_end: ${LIVEKIT_RTC_END}
  use_external_ip: true
keys:
  ${LIVEKIT_API_KEY}: ${LIVEKIT_API_SECRET}
logging:
  level: info
room:
  empty_timeout: 300
  max_participants: 10
agent:
  enabled: true
YAML

# Stop existing if running
docker stop livekit-server 2>/dev/null || true
docker rm livekit-server 2>/dev/null || true

# Run LiveKit
docker run -d \
  --name livekit-server \
  --restart unless-stopped \
  -p ${LIVEKIT_PORT}:7880 \
  -p ${LIVEKIT_RTC_START}-${LIVEKIT_RTC_END}:${LIVEKIT_RTC_START}-${LIVEKIT_RTC_END}/udp \
  -v ~/livekit-config/livekit.yaml:/etc/livekit.yaml:ro \
  livekit/livekit-server:v1.9.11 \
  --config /etc/livekit.yaml

echo "✅ LiveKit running on port ${LIVEKIT_PORT}"
echo ""
echo "Test: curl http://localhost:${LIVEKIT_PORT}/rtc/validate"
echo ""
echo "Next: Deploy voice agent with your server's IP or hostname:"
echo "  LIVEKIT_URL=ws://<YOUR_SERVER_IP>:${LIVEKIT_PORT}"
echo "  STT_URL=http://<YOUR_SERVER_IP>:9101"
echo "  TTS_URL=http://<YOUR_SERVER_IP>:9102"
echo "  LLM_URL=http://<YOUR_SERVER_IP>:9100/v1"
echo ""
echo "Replace <YOUR_SERVER_IP> with your actual server IP (e.g., 192.168.1.100)"
