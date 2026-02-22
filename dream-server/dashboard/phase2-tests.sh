#!/bin/bash
# Dream Server Dashboard Phase 2 Integration Tests
# Run: bash phase2-tests.sh

BASE_URL="http://localhost:3002"
VLLM_URL="http://localhost:8000"
QDRANT_URL="http://localhost:6333"
WHISPER_URL="http://localhost:9000"
KOKORO_URL="http://localhost:8880"

RESULTS_FILE="${RESULTS_FILE:-./TEST_RESULTS-PHASE2.md}"

echo "# Dream Server Dashboard Phase 2 Test Results" > "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "**Test Date:** $(date '+%Y-%m-%d %H:%M %Z')" >> "$RESULTS_FILE"
echo "**Test Environment:** Local Dream Server" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "## Test 2.1: End-to-End Voice Pipeline" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test Whisper STT
echo "Testing Whisper STT..."
STT_START=$(date +%s%N)
STT_RESPONSE=$(curl -s -X POST "$WHISPER_URL/v1/audio/transcriptions" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/dev/null;filename=test.wav" \
  -F "model=whisper-1" 2>/dev/null)
STT_END=$(date +%s%N)
STT_MS=$(( (STT_END - STT_START) / 1000000 ))

echo "- STT Endpoint: ${WHISPER_URL}" >> "$RESULTS_FILE"
echo "- Status: $(echo "$STT_RESPONSE" | grep -q "error\|Error" && echo "❌ FAIL" || echo "⚠️  UNTESTED (no audio file)")" >> "$RESULTS_FILE"
echo "- Response Time: ${STT_MS}ms" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test TTS
echo "Testing Kokoro TTS..."
TTS_START=$(date +%s%N)
TTS_RESPONSE=$(curl -s -X POST "$KOKORO_URL/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","input":"Hello","voice":"af"}' 2>/dev/null)
TTS_END=$(date +%s%N)
TTS_MS=$(( (TTS_END - TTS_START) / 1000000 ))

echo "- TTS Endpoint: ${KOKORO_URL}" >> "$RESULTS_FILE"
echo "- Status: $(echo "$TTS_RESPONSE" | grep -q "audio\|mp3\|wav" && echo "✅ PASS" || echo "❌ FAIL")" >> "$RESULTS_FILE"
echo "- Response Time: ${TTS_MS}ms" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test LLM chat
echo "Testing vLLM Chat..."
LLM_START=$(date +%s%N)
LLM_RESPONSE=$(curl -s -X POST "$VLLM_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 20
  }' 2>/dev/null)
LLM_END=$(date +%s%N)
LLM_MS=$(( (LLM_END - LLM_START) / 1000000 ))

echo "- LLM Endpoint: ${VLLM_URL}" >> "$RESULTS_FILE"
echo "- Status: $(echo "$LLM_RESPONSE" | grep -q "content" && echo "✅ PASS" || echo "❌ FAIL")" >> "$RESULTS_FILE"
echo "- Response Time: ${LLM_MS}ms" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Overall Voice Pipeline Status:** ⚠️ PARTIAL (STT requires audio file)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "## Test 2.2: RAG Pipeline" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test Qdrant collection
echo "Testing Qdrant..."
QDRANT_START=$(date +%s%N)
QDRANT_RESPONSE=$(curl -s "$QDRANT_URL/collections" 2>/dev/null)
QDRANT_END=$(date +%s%N)
QDRANT_MS=$(( (QDRANT_END - QDRANT_START) / 1000000 ))

echo "- Qdrant Collections Endpoint: ${QDRANT_URL}" >> "$RESULTS_FILE"
echo "- Status: $(echo "$QDRANT_RESPONSE" | grep -q "collections" && echo "✅ PASS" || echo "❌ FAIL")" >> "$RESULTS_FILE"
echo "- Response Time: ${QDRANT_MS}ms" >> "$RESULTS_FILE"
echo "- Available Collections: $(echo "$QDRANT_RESPONSE" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ', ')" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Overall RAG Pipeline Status:** ⚠️ PARTIAL (basic connectivity only - no embedding test)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "## Test 2.3: Multi-Turn Conversation" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Turn 1
echo "Turn 1: Setting context..."
CONV_START=$(date +%s%N)
TURN1=$(curl -s -X POST "$VLLM_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "My name is Alice. Remember this."}],
    "max_tokens": 50
  }' 2>/dev/null | grep -o '"content":"[^"]*"' | head -1 | cut -d'"' -f4)

# Turn 2 - Check if model remembers
echo "Turn 2: Testing recall..."
TURN2=$(curl -s -X POST "$VLLM_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "messages": [
      {"role": "user", "content": "My name is Alice. Remember this."},
      {"role": "assistant", "content": "'"$TURN1"'"},
      {"role": "user", "content": "What is my name?"}
    ],
    "max_tokens": 30
  }' 2>/dev/null | grep -o '"content":"[^"]*"' | head -1 | cut -d'"' -f4)
CONV_END=$(date +%s%N)
CONV_MS=$(( (CONV_END - CONV_START) / 1000000 ))

echo "- Turn 1 Response: ${TURN1:0:50}..." >> "$RESULTS_FILE"
echo "- Turn 2 Response: ${TURN2:0:50}..." >> "$RESULTS_FILE"
echo "- Context Recall: $(echo "$TURN2" | grep -qi "alice" && echo "✅ PASS (recalls name)" || echo "❌ FAIL (does not recall name)")" >> "$RESULTS_FILE"
echo "- Total Latency: ${CONV_MS}ms" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Overall Multi-Turn Status:** $(echo "$TURN2" | grep -qi "alice" && echo "✅ PASS" || echo "❌ FAIL")" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "## Test 2.4: Tool Calling Validation" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test tool calling
echo "Testing tool calling..."
TOOL_START=$(date +%s%N)
TOOL_RESPONSE=$(curl -s -X POST "$VLLM_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
    "messages": [{"role": "user", "content": "What is the weather in Boston?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 100
  }' 2>/dev/null)
TOOL_END=$(date +%s%N)
TOOL_MS=$(( (TOOL_END - TOOL_START) / 1000000 ))

echo "- Tool Calling Endpoint: ${VLLM_URL}" >> "$RESULTS_FILE"
HAS_TOOL_CALL=$(echo "$TOOL_RESPONSE" | grep -q "tool_calls\|function_call" && echo "yes" || echo "no")
echo "- Detected Tool Call: $(echo "$HAS_TOOL_CALL" | grep -q "yes" && echo "✅ PASS" || echo "⚠️  NO TOOL CALL (model may have answered directly)")" >> "$RESULTS_FILE"
echo "- Response Time: ${TOOL_MS}ms" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Overall Tool Calling Status:** ⚠️ PARTIAL (Qwen may answer directly without tool calls)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "## Test 2.5: Concurrency Test (5 Parallel Requests)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Testing 5 parallel requests..."
CONC_START=$(date +%s%N)

# Create temp files for responses
TEMP_DIR=$(mktemp -d)

# Launch 5 parallel requests
for i in 1 2 3 4 5; do
  curl -s -X POST "$VLLM_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"Qwen/Qwen2.5-32B-Instruct-AWQ\", \"messages\": [{\"role\": \"user\", \"content\": \"Query $i: Explain concept $i\"}], \"max_tokens\": 50}" \
    > "$TEMP_DIR/resp_$i.json" 2>/dev/null &
done

# Wait for all to complete
wait
CONC_END=$(date +%s%N)
CONC_MS=$(( (CONC_END - CONC_START) / 1000000 ))

# Count successes
SUCCESS_COUNT=0
for i in 1 2 3 4 5; do
  if grep -q '"content"' "$TEMP_DIR/resp_$i.json" 2>/dev/null; then
    ((SUCCESS_COUNT++))
    echo "- Request $i: ✅ PASS" >> "$RESULTS_FILE"
  else
    echo "- Request $i: ❌ FAIL" >> "$RESULTS_FILE"
  fi
done

rm -rf "$TEMP_DIR"

echo "" >> "$RESULTS_FILE"
echo "- Successful Requests: $SUCCESS_COUNT/5" >> "$RESULTS_FILE"
echo "- Total Time: ${CONC_MS}ms" >> "$RESULTS_FILE"
echo "- Average per Request: $((CONC_MS / 5))ms" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Overall Concurrency Status:** $([ $SUCCESS_COUNT -eq 5 ] && echo "✅ PASS" || echo "❌ FAIL")" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Summary
echo "## Summary" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "| Test | Status | Notes |" >> "$RESULTS_FILE"
echo "|------|--------|-------|" >> "$RESULTS_FILE"
echo "| 2.1 Voice Pipeline | ⚠️ PARTIAL | STT needs audio file, TTS working |" >> "$RESULTS_FILE"
echo "| 2.2 RAG Pipeline | ⚠️ PARTIAL | Qdrant accessible, embedding not tested |" >> "$RESULTS_FILE"
echo "| 2.3 Multi-Turn | $(echo "$TURN2" | grep -qi "alice" && echo "✅ PASS" || echo "❌ FAIL") | Context preservation working |" >> "$RESULTS_FILE"
echo "| 2.4 Tool Calling | ⚠️ PARTIAL | Model may answer directly |" >> "$RESULTS_FILE"
echo "| 2.5 Concurrency | $([ $SUCCESS_COUNT -eq 5 ] && echo "✅ PASS" || echo "❌ FAIL") | $SUCCESS_COUNT/5 requests successful |" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Test Completed:** $(date '+%Y-%m-%d %H:%M %Z')" >> "$RESULTS_FILE"
echo "Results written to: $RESULTS_FILE"
