#!/bin/bash
# M8 Missing Test: Concurrency Test
# Tests system stability under parallel load

VLLM_URL="http://localhost:8000"
MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ"
CONCURRENT_REQUESTS=5

echo "=== M8 Test: Concurrency ($CONCURRENT_REQUESTS parallel requests) ==="

# Create temp directory for responses
TEMP_DIR=$(mktemp -d)

# Launch concurrent requests
echo "  Launching $CONCURRENT_REQUESTS parallel requests..."
START=$(date +%s%N)

for i in $(seq 1 $CONCURRENT_REQUESTS); do
  (
    curl -s -X POST "$VLLM_URL/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"$MODEL\",
        \"messages\": [{\"role\": \"user\", \"content\": \"Test query $i: Explain concept $i\"}],
        \"max_tokens\": 30
      }" > "$TEMP_DIR/response_$i.json" 2>/dev/null
  ) &
done

# Wait for all to complete
wait
END=$(date +%s%N)
TOTAL_TIME=$(( (END - START) / 1000000 ))

# Count successes
SUCCESS=0
for i in $(seq 1 $CONCURRENT_REQUESTS); do
  if grep -q '"content"' "$TEMP_DIR/response_$i.json" 2>/dev/null; then
    SUCCESS=$((SUCCESS+1))
    echo "  ✅ Request $i: Success"
  else
    echo "  ❌ Request $i: Failed"
  fi
done

# Cleanup
rm -rf "$TEMP_DIR"

# Calculate metrics
AVG_TIME=$((TOTAL_TIME / CONCURRENT_REQUESTS))
SUCCESS_RATE=$(( SUCCESS * 100 / CONCURRENT_REQUESTS ))

echo ""
echo "  Total time: ${TOTAL_TIME}ms"
echo "  Average per request: ~${AVG_TIME}ms"
echo "  Success rate: $SUCCESS_RATE% ($SUCCESS/$CONCURRENT_REQUESTS)"

if [ $SUCCESS -eq $CONCURRENT_REQUESTS ]; then
  echo ""
  echo "✅ PASS: All $CONCURRENT_REQUESTS requests succeeded"
  exit 0
elif [ $SUCCESS -ge $(( CONCURRENT_REQUESTS * 4 / 5 )) ]; then
  echo ""
  echo "⚠️  PARTIAL: $SUCCESS/$CONCURRENT_REQUESTS succeeded (≥80%)"
  exit 0
else
  echo ""
  echo "❌ FAIL: Only $SUCCESS/$CONCURRENT_REQUESTS succeeded (<80%)"
  exit 1
fi
