#!/bin/bash

# Load environment variables from .env if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -E '^(WHISPER_PORT|TTS_PORT|EMBEDDINGS_PORT|VLLM_MODEL)=' "$ENV_FILE" | xargs)
fi
WHISPER_PORT="${WHISPER_PORT:-9000}"
TTS_PORT="${TTS_PORT:-8880}"
EMBEDDINGS_PORT="${EMBEDDINGS_PORT:-8090}"

# Function to check Docker container status
check_docker_containers() {
    echo "Checking Docker containers..."
    if ! docker ps --format '{{.Names}}: {{.Status}}' | grep -q 'Up'; then
        echo "ERROR: No running Docker containers found."
        return 1
    fi
    for container in $(docker ps --format '{{.Names}}'); do
        status=$(docker inspect -f '{{.State.Status}}' $container)
        if [ "$status" != "running" ]; then
            echo "ERROR: Container $container is not running."
            return 1
        fi
    done
    echo "All Docker containers are running."
    return 0
}

# Function to test vLLM API
check_vllm_api() {
    echo "Testing vLLM API..."
    # Get available model from vLLM, fallback to generic "default"
    model_name=$(curl -s http://localhost:8000/v1/models 2>/dev/null | grep -o '"id": "[^"]*"' | head -1 | cut -d'"' -f4)
    if [[ -z "$model_name" ]]; then
        model_name="default"
    fi
    response=$(curl -s -X POST http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\": \"$model_name\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}")
    if echo "$response" | grep -q '"error"'; then
        echo "ERROR: vLLM API test failed."
        return 1
    fi
    echo "vLLM API test passed."
    return 0
}

# Function to test Whisper STT endpoint
check_whisper_stt() {
    echo "Testing Whisper STT endpoint..."
    if ! curl -s http://localhost:${WHISPER_PORT}/health | grep -q 'OK'; then
        echo "ERROR: Whisper STT endpoint test failed."
        return 1
    fi
    echo "Whisper STT endpoint test passed."
    return 0
}

# Function to test TTS endpoint
check_tts_endpoint() {
    echo "Testing TTS endpoint..."
    if ! curl -s http://localhost:${TTS_PORT}/health | grep -q 'OK'; then
        echo "ERROR: TTS endpoint test failed."
        return 1
    fi
    echo "TTS endpoint test passed."
    return 0
}

# Function to test Qdrant vector DB
check_qdrant_db() {
    echo "Testing Qdrant vector DB..."
    if ! curl -s http://localhost:6333/collections | grep -q 'collections'; then
        echo "ERROR: Qdrant vector DB test failed."
        return 1
    fi
    echo "Qdrant vector DB test passed."
    return 0
}

# Main test function
run_tests() {
    local success=0
    local failure=0

    if check_docker_containers; then
        ((success++))
    else
        ((failure++))
    fi

    if check_vllm_api; then
        ((success++))
    else
        ((failure++))
    fi

    if check_whisper_stt; then
        ((success++))
    else
        ((failure++))
    fi

    if check_tts_endpoint; then
        ((success++))
    else
        ((failure++))
    fi

    if check_qdrant_db; then
        ((success++))
    else
        ((failure++))
    fi

    echo "Test Summary:"
    echo "Success: $success"
    echo "Failure: $failure"
}

run_tests
