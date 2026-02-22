# LiveKit Server with Environment Variable Support
# Adds envsubst for runtime config generation

FROM livekit/livekit-server:v1.9.11

# Install envsubst (from gettext) — livekit base image is Alpine
USER root
RUN apk add --no-cache gettext

# Copy entrypoint script
COPY livekit-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/livekit-entrypoint.sh

# Use non-root user
USER 1000:1000

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/livekit-entrypoint.sh"]
CMD ["--config", "/tmp/livekit.yaml"]
