#!/bin/bash
# Dream Server Dashboard Phase 3 Benchmark Suite
# Run: bash phase3-benchmarks.sh

VLLM_URL="http://localhost:8000"
RESULTS_FILE="${RESULTS_FILE:-./TEST_RESULTS-PHASE3.md}"
MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ"

echo "# Dream Server Dashboard Phase 3 Benchmark Results" > "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "**Test Date:** $(date '+%Y-%m-%d %H:%M %Z')" >> "$RESULTS_FILE"
echo "**Test Environment:** Local Dream Server" >> "$RESULTS_FILE"
echo "**Model:** $MODEL" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Helper function for timing
measure_request() {
    local prompt="$1"
    local max_tokens="${2:-50}"
    
    START=$(date +%s%N)
    RESPONSE=$(curl -s -X POST "$VLLM_URL/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}], \"max_tokens\": $max_tokens}" \
        2>/dev/null)
    END=$(date +%s%N)
    
    TTFT=$(( (END - START) / 1000000 ))
    echo "$TTFT"
}

# ============================================
# Test 3.1: Latency Benchmarks
# ============================================
echo "## Test 3.1: Latency Benchmarks" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Running latency benchmarks (20 requests)..."

TTFT_VALUES=()
for i in $(seq 1 20); do
    case $((i % 3)) in
        0) PROMPT="Say hello" ; TOKENS=20 ;;
        1) PROMPT="Explain quantum computing in simple terms" ; TOKENS=150 ;;
        2) PROMPT="Write a comprehensive guide to local AI deployment" ; TOKENS=200 ;;
    esac
    
    TTFT=$(measure_request "$PROMPT" $TOKENS)
    TTFT_VALUES+=($TTFT)
    echo "  Request $i: ${TTFT}ms"
done

# Calculate statistics
SUM=0
MIN=${TTFT_VALUES[0]}
MAX=${TTFT_VALUES[0]}
for val in "${TTFT_VALUES[@]}"; do
    SUM=$((SUM + val))
    [ $val -lt $MIN ] && MIN=$val
    [ $val -gt $MAX ] && MAX=$val
done
AVG=$((SUM / ${#TTFT_VALUES[@]}))

# Sort for percentiles
IFS=$'\n' SORTED=($(sort -n <<<"${TTFT_VALUES[*]}")); unset IFS
P50=${SORTED[9]}
P95=${SORTED[18]}

echo "" >> "$RESULTS_FILE"
echo "### Results" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "| Metric | Value |" >> "$RESULTS_FILE"
echo "|--------|-------|" >> "$RESULTS_FILE"
echo "| Requests | 20 |" >> "$RESULTS_FILE"
echo "| Min TTFT | ${MIN}ms |" >> "$RESULTS_FILE"
echo "| Max TTFT | ${MAX}ms |" >> "$RESULTS_FILE"
echo "| Avg TTFT | ${AVG}ms |" >> "$RESULTS_FILE"
echo "| p50 TTFT | ${P50}ms |" >> "$RESULTS_FILE"
echo "| p95 TTFT | ${P95}ms |" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

PASS_CRITERIA=1000
if [ $P95 -lt $PASS_CRITERIA ]; then
    echo "**Status: ✅ PASS** (p95 TTFT < 1s)" >> "$RESULTS_FILE"
else
    echo "**Status: ❌ FAIL** (p95 TTFT > 1s)" >> "$RESULTS_FILE"
fi
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# ============================================
# Test 3.2: Concurrent User Simulation
# ============================================
echo "## Test 3.2: Concurrent User Simulation" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

run_concurrent_test() {
    local USERS=$1
    local ITERATIONS=$2
    
    echo "Testing $USERS concurrent users ($ITERATIONS iterations)..."
    
    SUCCESS=0
    TOTAL=$((USERS * ITERATIONS))
    TEMP_DIR=$(mktemp -d)
    
    for iter in $(seq 1 $ITERATIONS); do
        # Launch concurrent requests
        for user in $(seq 1 $USERS); do
            (
                sleep $(awk "BEGIN {printf \"%.2f\", rand()*0.1}")
                curl -s -X POST "$VLLM_URL/v1/chat/completions" \
                    -H "Content-Type: application/json" \
                    -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello from user $user\"}], \"max_tokens\": 30}" \
                    > "$TEMP_DIR/resp_${iter}_${user}.json" 2>/dev/null
            ) &
        done
        wait
    done
    
    # Count successes
    for iter in $(seq 1 $ITERATIONS); do
        for user in $(seq 1 $USERS); do
            if grep -q '"content"' "$TEMP_DIR/resp_${iter}_${user}.json" 2>/dev/null; then
                ((SUCCESS++))
            fi
        done
    done
    
    rm -rf "$TEMP_DIR"
    
    SUCCESS_RATE=$((SUCCESS * 100 / TOTAL))
    echo "$SUCCESS/$TOTAL ($SUCCESS_RATE%)"
}

echo "### 10 Concurrent Users" >> "$RESULTS_FILE"
RESULT_10=$(run_concurrent_test 10 5)
echo "- Result: $RESULT_10" >> "$RESULTS_FILE"
TEST10_PASS=$(echo "$RESULT_10" | grep -q "100" && echo "✅" || echo "❌")
echo "- Status: $TEST10_PASS" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "### 25 Concurrent Users" >> "$RESULTS_FILE"
RESULT_25=$(run_concurrent_test 25 5)
echo "- Result: $RESULT_25" >> "$RESULTS_FILE"
TEST25_RATE=$(echo "$RESULT_25" | grep -oP '\d+(?=%)')
if [ "$TEST25_RATE" -ge 95 ]; then
    echo "- Status: ✅ PASS (>95%)" >> "$RESULTS_FILE"
else
    echo "- Status: ❌ FAIL (<95%)" >> "$RESULTS_FILE"
fi
echo "" >> "$RESULTS_FILE"

echo "### 50 Concurrent Users" >> "$RESULTS_FILE"
RESULT_50=$(run_concurrent_test 50 3)
echo "- Result: $RESULT_50" >> "$RESULTS_FILE"
TEST50_RATE=$(echo "$RESULT_50" | grep -oP '\d+(?=%)')
if [ "$TEST50_RATE" -ge 90 ]; then
    echo "- Status: ✅ PASS (>90%)" >> "$RESULTS_FILE"
else
    echo "- Status: ⚠️ PARTIAL (<90%)" >> "$RESULTS_FILE"
fi
echo "" >> "$RESULTS_FILE"

echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# ============================================
# Test 3.3: Memory Leak Detection
# ============================================
echo "## Test 3.3: Memory Leak Detection" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Checking memory usage patterns..."
echo "Note: Full leak detection requires GPU monitoring (nvidia-smi)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Get initial memory if possible
if command -v nvidia-smi &> /dev/null; then
    BASELINE_VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    echo "- Baseline GPU VRAM: ${BASELINE_VRAM}MB" >> "$RESULTS_FILE"
else
    echo "- Baseline GPU VRAM: n/a (nvidia-smi not available)" >> "$RESULTS_FILE"
    BASELINE_VRAM=0
fi

echo "Running 50 sequential conversations..."
for i in $(seq 1 50); do
    curl -s -X POST "$VLLM_URL/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"Turn $i: Brief response\"}], \"max_tokens\": 20}" \
        > /dev/null 2>&1
    
    if [ $((i % 10)) -eq 0 ]; then
        echo "  Progress: $i/50"
    fi
done

if [ "$BASELINE_VRAM" -gt 0 ]; then
    FINAL_VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    VRAM_INCREASE=$((FINAL_VRAM - BASELINE_VRAM))
    VRAM_PCT=$((VRAM_INCREASE * 100 / BASELINE_VRAM))
    
    echo "- Final GPU VRAM: ${FINAL_VRAM}MB" >> "$RESULTS_FILE"
    echo "- VRAM Change: ${VRAM_INCREASE}MB (${VRAM_PCT}%)" >> "$RESULTS_FILE"
    
    if [ $VRAM_PCT -lt 10 ]; then
        echo "**Status: ✅ PASS** (<10% increase)" >> "$RESULTS_FILE"
    else
        echo "**Status: ⚠️ REVIEW** (>10% increase)" >> "$RESULTS_FILE"
    fi
else
    echo "- VRAM monitoring not available in test environment" >> "$RESULTS_FILE"
    echo "**Status: ⚠️ SKIPPED** (no GPU monitoring)" >> "$RESULTS_FILE"
fi
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# ============================================
# Summary
# ============================================
echo "## Summary" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "| Test | Status | Key Metric |" >> "$RESULTS_FILE"
echo "|------|--------|------------|" >> "$RESULTS_FILE"
echo "| 3.1 Latency | $([ $P95 -lt 1000 ] && echo "✅ PASS" || echo "❌ FAIL") | p95 TTFT: ${P95}ms |" >> "$RESULTS_FILE"
echo "| 3.2 10 Users | $TEST10_PASS | $RESULT_10 |" >> "$RESULTS_FILE"
echo "| 3.2 25 Users | $([ "$TEST25_RATE" -ge 95 ] && echo "✅ PASS" || echo "❌ FAIL") | $RESULT_25 |" >> "$RESULTS_FILE"
echo "| 3.2 50 Users | $([ "$TEST50_RATE" -ge 90 ] && echo "✅ PASS" || echo "⚠️ PARTIAL") | $RESULT_50 |" >> "$RESULTS_FILE"
echo "| 3.3 Memory | $([ $VRAM_PCT -lt 10 ] 2>/dev/null && echo "✅ PASS" || echo "⚠️ SKIPPED") | $([ -n "$VRAM_PCT" ] && echo "${VRAM_PCT}% increase" || echo "N/A") |" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Test Completed:** $(date '+%Y-%m-%d %H:%M %Z')" >> "$RESULTS_FILE"
echo "Results written to: $RESULTS_FILE"
echo ""
echo "Phase 3 benchmarks complete. Check $RESULTS_FILE for detailed results."
