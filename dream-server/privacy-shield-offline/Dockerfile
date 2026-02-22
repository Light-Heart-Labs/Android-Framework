# API Privacy Shield - OFFLINE MODE
# Zero-cloud PII proxy with local-only API routing
# M1 Phase 2 - M3 Security Component
#
# Build: docker build -t privacy-shield-offline .
# Run:   docker run -p 8085:8085 --network dream-network-offline privacy-shield-offline

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY proxy.py .
COPY pii_scrubber.py .

# Create non-root user
RUN useradd -m -u 1000 shield && chown -R shield:shield /app
USER shield

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8085/health')" || exit 1

EXPOSE 8085

CMD ["python", "proxy.py"]
