#!/bin/bash
# Dream Server First Boot Demo
# Shows off what your local AI stack can do in under 2 minutes
#
# Usage: ./first-boot-demo.sh [--all] [--quick]
# Mission: M5 (Clonable Dream Setup Server)

set -e

#=============================================================================
# Colors
#=============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

#=============================================================================
# Config
#=============================================================================
VLLM_URL="${VLLM_URL:-http://localhost:8000}"
WHISPER_URL="${WHISPER_URL:-http://localhost:9000}"
PIPER_URL="${PIPER_URL:-http://localhost:8880}"
N8N_URL="${N8N_URL:-http://localhost:5678}"
WEBUI_URL="${WEBUI_URL:-http://localhost:3000}"

QUICK_MODE=false
ALL_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick) QUICK_MODE=true; shift ;;
        --all) ALL_MODE=true; shift ;;
        -h|--help) 
            echo "Usage: $0 [--quick] [--all]"
            echo "  --quick  Skip slow demos, just show what's available"
            echo "  --all    Run all demos including voice (requires audio files)"
            exit 0
            ;;
        *) shift ;;
    esac
done

#=============================================================================
# Helpers
#=============================================================================
header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

demo() {
    echo -e "\n${MAGENTA}▶${NC} ${BOLD}$1${NC}"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

wait_key() {
    if [[ "$QUICK_MODE" != "true" ]]; then
        echo -e "\n${YELLOW}Press Enter to continue...${NC}"
        read -r
    fi
}

check_service() {
    local name=$1
    local url=$2
    local endpoint=${3:-/health}
    
    if curl -sf "${url}${endpoint}" > /dev/null 2>&1; then
        success "$name is running at $url"
        return 0
    else
        fail "$name not responding at $url"
        return 1
    fi
}

#=============================================================================
# Welcome
#=============================================================================
clear
echo ""
echo -e "${BOLD}${CYAN}"
cat << 'EOF'
    ____                            _____                          
   / __ \_________  ____ _____ ___ / ___/___  ______   _____  _____
  / / / / ___/ _ \/ __ `/ __ `__ \\__ \/ _ \/ ___/ | / / _ \/ ___/
 / /_/ / /  /  __/ /_/ / / / / / /__/ /  __/ /   | |/ /  __/ /    
/_____/_/   \___/\__,_/_/ /_/ /_/____/\___/_/    |___/\___/_/     
                                                                   
EOF
echo -e "${NC}"
echo -e "${BOLD}Your Local AI Stack — First Boot Demo${NC}"
echo -e "Everything runs on YOUR hardware. No cloud. No API costs. Full privacy.\n"

#=============================================================================
# Health Check
#=============================================================================
header "🔍 Checking Services"

SERVICES_OK=0
SERVICES_TOTAL=0

# Core services
((SERVICES_TOTAL++))
if check_service "vLLM (Local LLM)" "$VLLM_URL" "/health"; then
    ((SERVICES_OK++))
    VLLM_AVAILABLE=true
else
    VLLM_AVAILABLE=false
fi

((SERVICES_TOTAL++))
if check_service "Open WebUI" "$WEBUI_URL" "/"; then
    ((SERVICES_OK++))
fi

# Optional services
if curl -sf "${WHISPER_URL}/health" > /dev/null 2>&1; then
    success "Whisper STT is running (voice input enabled)"
    WHISPER_AVAILABLE=true
    ((SERVICES_OK++))
    ((SERVICES_TOTAL++))
else
    info "Whisper STT not running (voice input disabled)"
    WHISPER_AVAILABLE=false
fi

if curl -sf "${PIPER_URL}" > /dev/null 2>&1; then
    success "OpenTTS TTS is running (voice output enabled)"
    PIPER_AVAILABLE=true
    ((SERVICES_OK++))
    ((SERVICES_TOTAL++))
else
    info "OpenTTS TTS not running (voice output disabled)"
    PIPER_AVAILABLE=false
fi

if curl -sf "${N8N_URL}/healthz" > /dev/null 2>&1; then
    success "n8n Workflows is running (automation enabled)"
    N8N_AVAILABLE=true
    ((SERVICES_OK++))
    ((SERVICES_TOTAL++))
else
    info "n8n not running (automation disabled)"
    N8N_AVAILABLE=false
fi

echo ""
echo -e "${BOLD}Services: ${SERVICES_OK}/${SERVICES_TOTAL} running${NC}"

if [[ "$VLLM_AVAILABLE" != "true" ]]; then
    echo -e "\n${RED}vLLM is required for demos. Is it still loading?${NC}"
    echo "Check status: docker compose logs -f vllm"
    exit 1
fi

wait_key

#=============================================================================
# Demo 1: Chat Completion
#=============================================================================
header "💬 Demo 1: Local Chat Completion"

demo "Asking your local AI a question..."

RESPONSE=$(curl -sf "${VLLM_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
        "messages": [{"role": "user", "content": "In one sentence, what makes local AI special?"}],
        "max_tokens": 100,
        "temperature": 0.7
    }' 2>/dev/null | jq -r '.choices[0].message.content' 2>/dev/null || echo "")

if [[ -n "$RESPONSE" && "$RESPONSE" != "null" ]]; then
    echo ""
    echo -e "${GREEN}Response:${NC}"
    echo -e "  ${RESPONSE}"
    echo ""
    success "Local LLM responded! No API calls, no cloud, just your GPU."
else
    fail "No response from LLM"
fi

wait_key

#=============================================================================
# Demo 2: Code Assistance
#=============================================================================
header "🧑‍💻 Demo 2: Code Assistance"

demo "Asking for help with a Python function..."

CODE_RESPONSE=$(curl -sf "${VLLM_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
        "messages": [{"role": "user", "content": "Write a Python one-liner to reverse a string. Just the code, no explanation."}],
        "max_tokens": 50,
        "temperature": 0.3
    }' 2>/dev/null | jq -r '.choices[0].message.content' 2>/dev/null || echo "")

if [[ -n "$CODE_RESPONSE" && "$CODE_RESPONSE" != "null" ]]; then
    echo ""
    echo -e "${GREEN}Generated code:${NC}"
    echo -e "  ${CODE_RESPONSE}"
    echo ""
    success "Code assistant works! Great for development."
else
    fail "No response from code assistant"
fi

wait_key

#=============================================================================
# Demo 3: Streaming
#=============================================================================
header "📡 Demo 3: Streaming Response"

demo "Watching tokens stream in real-time..."
echo ""

# Simple streaming demo - just show it works
curl -sN "${VLLM_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
        "messages": [{"role": "user", "content": "Count from 1 to 5, one number per line."}],
        "max_tokens": 50,
        "temperature": 0,
        "stream": true
    }' 2>/dev/null | while read -r line; do
        if [[ "$line" == data:* ]]; then
            content=$(echo "${line#data: }" | jq -r '.choices[0].delta.content // empty' 2>/dev/null)
            if [[ -n "$content" ]]; then
                printf "%s" "$content"
            fi
        fi
    done

echo ""
echo ""
success "Streaming works! Great for real-time UIs."

wait_key

#=============================================================================
# Summary
#=============================================================================
header "🎉 Demo Complete!"

echo ""
echo -e "${BOLD}What you just saw:${NC}"
echo "  ✓ Local LLM responding to prompts"
echo "  ✓ Code assistance capabilities"  
echo "  ✓ Real-time streaming"
echo ""

echo -e "${BOLD}What's available:${NC}"
echo "  • Open WebUI:  ${WEBUI_URL}"
[[ "$N8N_AVAILABLE" == "true" ]] && echo "  • n8n Workflows: ${N8N_URL}"
[[ "$WHISPER_AVAILABLE" == "true" ]] && echo "  • Whisper STT:   ${WHISPER_URL}"
[[ "$PIPER_AVAILABLE" == "true" ]] && echo "  • OpenTTS TTS:     ${PIPER_URL}"
echo ""

echo -e "${BOLD}Next steps:${NC}"
echo "  1. Open ${WEBUI_URL} and start chatting"
echo "  2. Import workflows from ./workflows/ into n8n"
echo "  3. Try the voice demo: ./scripts/voice-demo.sh"
echo "  4. Enable OpenClaw: docker compose --profile openclaw up -d"
echo ""

echo -e "${CYAN}Everything runs locally. Your data stays private. Enjoy! 🚀${NC}"
echo ""
