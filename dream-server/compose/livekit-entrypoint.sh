#!/bin/bash
# LiveKit Server Entrypoint with Template Substitution
# Replaces environment variables in livekit.yaml.template → livekit.yaml

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

# Substitute environment variables in template
envsubst < /etc/livekit.yaml.template > /etc/livekit.yaml

# Run LiveKit with the generated config
exec livekit-server --config /etc/livekit.yaml "$@"
