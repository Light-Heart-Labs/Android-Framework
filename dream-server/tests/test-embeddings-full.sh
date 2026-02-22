#!/bin/bash
# M8 Missing Test: Embeddings Full Test
# Tests actual embedding vector generation

VLLM_URL="http://localhost:8000"

echo "=== M8 Test: Embeddings Full ==="

TEST_TEXT="The quick brown fox jumps over the lazy dog"

# Test embeddings endpoint
START=$(date +%s%N)
RESPONSE=$(curl -s -X POST "$VLLM_URL/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"Qwen/Qwen2.5-32B-Instruct-AWQ\",
    \"input\": \"$TEST_TEXT\"
  }" 2>/dev/null)
END=$(date +%s%N)
LATENCY=$(( (END - START) / 1000000 ))

# Check for embedding array
if echo "$RESPONSE" | grep -q '"embedding":\['; then
  # Extract vector dimension
  DIM=$(echo "$RESPONSE" | grep -o '"embedding":\[[^]]*\]' | head -1 | tr ',' '\n' | wc -l)
  echo "✅ PASS: Embeddings generated (${LATENCY}ms, ${DIM} dimensions)"
  exit 0
else
  echo "❌ FAIL: No embedding vector in response (${LATENCY}ms)"
  echo "   Response: ${RESPONSE:0:100}"
  exit 1
fi
