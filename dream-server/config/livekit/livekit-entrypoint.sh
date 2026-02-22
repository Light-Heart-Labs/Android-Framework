#!/bin/sh
# livekit-entrypoint.sh
# Substitutes environment variables in LiveKit config and starts server

set -e

CONFIG_TEMPLATE="/etc/livekit.yaml.template"
CONFIG_OUTPUT="/tmp/livekit.yaml"

# Check if template exists
if [ -f "$CONFIG_TEMPLATE" ]; then
    echo "Generating LiveKit config from template..."
    
    # Check required env vars
    if [ -z "${LIVEKIT_API_KEY:-}" ]; then
        echo "ERROR: LIVEKIT_API_KEY environment variable is required"
        exit 1
    fi
    
    if [ -z "${LIVEKIT_API_SECRET:-}" ]; then
        echo "ERROR: LIVEKIT_API_SECRET environment variable is required"
        exit 1
    fi
    
    # Substitute environment variables
    envsubst < "$CONFIG_TEMPLATE" > "$CONFIG_OUTPUT"
    echo "LiveKit config generated successfully"
else
    echo "ERROR: Config template not found at $CONFIG_TEMPLATE"
    exit 1
fi

# Execute the original LiveKit server command
exec /livekit-server "$@"
