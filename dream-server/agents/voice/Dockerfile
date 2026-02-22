# Dream Server Voice Agent
# Real-time voice chat using LiveKit + local LLM
#
# Build: docker build -t dream-voice-agent .
# Run:   docker run -e LLM_URL=... -e STT_URL=... dream-voice-agent

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
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Non-root user for security
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

# Run the agent
CMD ["./entrypoint.sh"]
