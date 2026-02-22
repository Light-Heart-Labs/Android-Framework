FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask requests
COPY vllm-tool-proxy.py .
EXPOSE 8003
CMD ["python3", "vllm-tool-proxy.py", "--port", "8003"]
