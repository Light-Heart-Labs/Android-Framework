# Dream Server Voice Agent - OFFLINE MODE
# Local-only voice chat using LiveKit + local LLM
# M1 Phase 2 - Zero cloud dependencies
#
# Build: docker build -t dream-voice-agent-offline .
# Run:   docker run --network dream-network-offline dream-voice-agent-offline

FROM python:3.11-slim

WORKDIR /app

# Install system deps (portaudio for audio, ffmpeg for transcoding)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    ffmpeg \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copy deterministic module
COPY deterministic/ ./deterministic/

# Copy offline-specific flows
COPY flows/ ./flows/

# Create health check endpoint
COPY health_check.py .

# Non-root user for security
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

# Run the agent
CMD ["./entrypoint.sh"]