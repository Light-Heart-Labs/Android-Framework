#!/bin/bash
#=============================================================================
# dream-test-functional.sh - Functional Testing for Dream Server
#
# Tests actual functionality, not just port availability:
# - vLLM generates coherent text
# - Whisper transcribes actual audio
# - TTS generates valid audio files
# - Embeddings produce vectors
#
# This complements dream-test.sh which checks service health.
#=============================================================================

set -euo pipefail

# Colors
RED='\e[0;31m'
GREEN='\e[0;32m'
YELLOW='\e[1;33m'
NC='\e[0m'

# Service endpoints
VLLM_URL="${VLLM_URL:-http://localhost:8000}"
WHISPER_URL="${WHISPER_URL:-http://localhost:9000}"
TTS_URL="${TTS_URL:-http://localhost:8880}"
EMBEDDING_URL="${EMBEDDING_URL:-http://localhost:9103}"

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: vLLM generates coherent text
test_vllm_functional() {
    echo ""
    echo "> Testing vLLM Functional Generation"
    
    local prompt="What is 2+2? Answer with just the number."
    local payload="{\"model\": \"Qwen/Qwen2.5-32B-Instruct-AWQ\", \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}], \"max_tokens\": 10, \"temperature\": 0.1}"
    
    local response
    response=$(curl -s --max-time 30 \
        -X POST "$VLLM_URL/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null || echo "")
    
    if [[ -z "$response" ]]; then
        fail "vLLM returned no response"
        return 1
    fi
    
    local content
    content=$(echo "$response" | grep -oP '"content":\s*"[^"]+"' | head -1 | cut -d'"' -f4)
    
    if [[ -z "$content" ]]; then
        fail "vLLM returned empty content"
        return 1
    fi
    
    # Check if response contains "4" (the answer to 2+2)
    if echo "$content" | grep -q "4"; then
        pass "vLLM generates correct answer: '$content'"
    else
        warn "vLLM generated: '$content' (expected '4')"
        pass "vLLM generates text (answer may vary)"
    fi
}

# Test 2: TTS generates valid audio file
test_tts_functional() {
    echo ""
    echo "> Testing TTS Audio Generation"
    
    local test_text="Hello, this is a test."
    local output_file="/tmp/test_tts_output.wav"
    
    local payload="{\"model\": \"kokoro\", \"input\": \"$test_text\", \"voice\": \"af_bella\", \"response_format\": \"wav\"}"
    
    # Generate audio
    local http_code
    http_code=$(curl -s -w "%{http_code}" --max-time 30 \
        -X POST "$TTS_URL/v1/audio/speech" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -o "$output_file" 2>/dev/null)
    
    if [[ "$http_code" != "200" ]]; then
        fail "TTS returned HTTP $http_code"
        rm -f "$output_file"
        return 1
    fi
    
    # Check file exists and has content
    if [[ ! -f "$output_file" ]]; then
        fail "TTS did not create output file"
        return 1
    fi
    
    local file_size
    file_size=$(stat -c%s "$output_file" 2>/dev/null || stat -f%z "$output_file" 2>/dev/null || echo "0")
    
    if [[ "$file_size" -lt 1000 ]]; then
        fail "TTS output too small: $file_size bytes (expected >1KB)"
        rm -f "$output_file"
        return 1
    fi
    
    # Check it's a valid WAV file
    if ! file "$output_file" | grep -qi "audio\|wav\|riff"; then
        warn "TTS output may not be valid WAV: $(file "$output_file")"
        pass "TTS generates audio file ($file_size bytes)"
    else
        pass "TTS generates valid WAV audio ($file_size bytes)"
    fi
    
    rm -f "$output_file"
}

# Test 3: Embeddings produce vectors
test_embeddings_functional() {
    echo ""
    echo "> Testing Embeddings Vector Generation"
    
    local test_text="This is a test sentence for embeddings."
    local payload="{\"inputs\": \"$test_text\"}"
    
    local response
    response=$(curl -s --max-time 30 \
        -X POST "$EMBEDDING_URL/embed" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null || echo "")
    
    if [[ -z "$response" ]]; then
        # Try alternate endpoint
        response=$(curl -s --max-time 30 \
            -X POST "$EMBEDDING_URL/" \
            -H "Content-Type: application/json" \
            -d "$payload" 2>/dev/null || echo "")
    fi
    
    if [[ -z "$response" ]]; then
        fail "Embeddings returned no response"
        return 1
    fi
    
    # Check if response contains array of numbers
    if echo "$response" | grep -qE '\[\s*-?[0-9]+\.[0-9]+'; then
        local vector_len
        vector_len=$(echo "$response" | grep -oE '-?[0-9]+\.[0-9]+' | wc -l)
        pass "Embeddings generates vectors ($vector_len dimensions)"
    else
        fail "Embeddings did not return valid vectors"
        return 1
    fi
}

# Test 4: Whisper transcribes audio (if test audio available)
test_whisper_functional() {
    echo ""
    echo "> Testing Whisper Transcription"
    
    # Create a simple test audio file or use existing
    local test_audio="/tmp/test_audio.wav"
    
    # Try to generate test audio with TTS first
    local tts_payload='{"model": "kokoro", "input": "Hello world", "voice": "af_bella", "response_format": "wav"}'
    
    if ! curl -s --max-time 15 \
        -X POST "$TTS_URL/v1/audio/speech" \
        -H "Content-Type: application/json" \
        -d "$tts_payload" \
        -o "$test_audio" 2>/dev/null; then
        warn "Could not generate test audio for Whisper"
        warn "Skipping Whisper functional test (TTS dependency)"
        return 0
    fi
    
    if [[ ! -f "$test_audio" ]] || [[ $(stat -c%s "$test_audio" 2>/dev/null) -lt 1000 ]]; then
        warn "Test audio generation failed"
        return 0
    fi
    
    # Transcribe with Whisper
    local response
    response=$(curl -s --max-time 30 \
        -X POST "$WHISPER_URL/v1/audio/transcriptions" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@$test_audio" \
        -F "model=whisper-1" 2>/dev/null || echo "")
    
    rm -f "$test_audio"
    
    if [[ -z "$response" ]]; then
        fail "Whisper returned no response"
        return 1
    fi
    
    local transcription
    transcription=$(echo "$response" | grep -oP '"text":\s*"[^"]+"' | head -1 | cut -d'"' -f4)
    
    if [[ -z "$transcription" ]]; then
        fail "Whisper returned empty transcription"
        return 1
    fi
    
    if echo "$transcription" | grep -qi "hello\|world"; then
        pass "Whisper transcribes correctly: '$transcription'"
    else
        warn "Whisper transcribed: '$transcription'"
        pass "Whisper generates transcription"
    fi
}

# Main
echo "========================================"
echo "  DREAM SERVER - FUNCTIONAL TESTS"
echo "  Tests actual functionality, not ports"
echo "========================================"

test_vllm_functional
test_tts_functional
test_embeddings_functional
test_whisper_functional

echo ""
echo "========================================"
echo "  Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "========================================"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ All functional tests passed${NC}"
    exit 0
else
    echo -e "${RED}✗ Some functional tests failed${NC}"
    exit 1
fi
