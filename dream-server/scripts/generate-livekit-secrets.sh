#!/bin/bash
# generate-livekit-secrets.sh
# Generates random LiveKit API keys and secrets for Dream Server
# Run this before first install to create secure credentials

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

# Generate cryptographically secure random strings
# API key: 16 chars alphanumeric
API_KEY=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 16)

# API secret: 32 chars alphanumeric
API_SECRET=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 32)

echo "=== LiveKit Secret Generation ==="
echo "API Key: ${API_KEY}"
echo "API Secret: ${API_SECRET:0:8}... (hidden)"
echo ""

# Check if .env exists
if [[ -f "${ENV_FILE}" ]]; then
    echo "Found existing .env file"
    
    # Backup existing .env
    cp "${ENV_FILE}" "${ENV_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
    echo "Backed up existing .env"
    
    # Remove old LiveKit vars if they exist
    sed -i '/^LIVEKIT_API_KEY=/d' "${ENV_FILE}"
    sed -i '/^LIVEKIT_API_SECRET=/d' "${ENV_FILE}"
    echo "Removed existing LiveKit credentials"
else
    echo "Creating new .env file"
    touch "${ENV_FILE}"
fi

# Append new secrets
cat >> "${ENV_FILE}" << EOF

# LiveKit API Credentials (auto-generated $(date +%Y-%m-%d))
LIVEKIT_API_KEY=${API_KEY}
LIVEKIT_API_SECRET=${API_SECRET}
EOF

echo ""
echo "=== LiveKit secrets added to .env ==="
echo "File: ${ENV_FILE}"
echo ""
echo "Next steps:"
echo "1. Review ${ENV_FILE} to verify credentials"
echo "2. Run: docker compose up -d livekit"
echo "3. Update voice agent configs to use these credentials"
