#!/bin/bash
# M8 Missing Test: Streaming Test
# Tests LLM streaming responses

VLLM_URL="http://localhost:8000"
MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ"

echo "=== M8 Test: Streaming ==="

# Test streaming endpoint
START=$(date +%s%N)
RESPONSE=$(curl -s -N -X POST "$VLLM_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Count to 5\"}],
    \"stream\": true,
    \"max_tokens\": 20
  }" 2>/dev/null | head -c 500)
END=$(date +%s%N)
LATENCY=$(( (END - START) / 1000000 ))

# Check for streaming data prefix (should contain "data:")
if echo "$RESPONSE" | grep -q "data:"; then
  echo "✅ PASS: Streaming response received (${LATENCY}ms)"
  exit 0
else
  echo "❌ FAIL: No streaming data detected (${LATENCY}ms)"
  echo "Response preview: ${RESPONSE:0:100}"
  exit 1
fi
