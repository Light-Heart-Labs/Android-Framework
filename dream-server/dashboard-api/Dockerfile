# Dream Server Dashboard API
# Lightweight system status backend for the Dashboard UI

FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/Light-Heart-Labs/Lighthouse-AI"
LABEL org.opencontainers.image.description="Dream Server Dashboard API"

WORKDIR /app

# Install system deps for nvidia-smi access and PostgreSQL (asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .
COPY agent_monitor.py .
COPY model_manager.py .

# Non-root user
RUN useradd -m -u 1000 dreamer

# B1 fix: Create /data directory and make it writable for API key generation
RUN mkdir -p /data && chown dreamer:dreamer /data

USER dreamer

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3002/health || exit 1

EXPOSE 3002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3002"]
