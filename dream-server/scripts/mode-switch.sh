#!/bin/bash
# Dream Server Mode Switch
# Usage: ./mode-switch.sh [cloud|local|hybrid|status]
#
# Part of M1 Zero-Cloud Initiative - Phase 3

set -e

#=============================================================================
# Configuration
#=============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DREAM_DIR="${SCRIPT_DIR}/.."
MODE_FILE="${DREAM_DIR}/.current-mode"
DEFAULT_MODE="cloud"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

#=============================================================================
# Helpers
#=============================================================================
log() { echo -e "${CYAN}[dream-mode]${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }

# Auto-detect docker compose command availability
get_docker_compose_cmd() {
    if docker compose version &>/dev/null; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# Get local model path from compose file (handles both Qwen2.5-32B and Qwen2.5-Coder-32B)
get_local_model_path() {
    local compose_file="${DREAM_DIR}/docker-compose.local.yml"
    if [[ -f "$compose_file" ]]; then
        grep -o 'Qwen/Qwen2\.5[^ ]*AWQ' "$compose_file" 2>/dev/null | head -1
    fi
}

get_current_mode() {
    if [[ -f "$MODE_FILE" ]]; then
        cat "$MODE_FILE"
    else
        echo "$DEFAULT_MODE"
    fi
}

save_mode() {
    echo "$1" > "$MODE_FILE"
}

#=============================================================================
# Mode Information
#=============================================================================
print_mode_info() {
    local mode=$1
    echo ""
    case "$mode" in
        cloud)
            echo -e "${BLUE}━━━ Cloud Mode ━━━${NC}"
            echo "  • LiteLLM gateway with cloud model access"
            echo "  • Requires API keys: ANTHROPIC_API_KEY, OPENAI_API_KEY"
            echo "  • Best quality, internet required"
            echo "  • Cost: ~\$0.003-0.06/1K tokens"
            echo ""
            echo -e "${YELLOW}Requirements:${NC}"
            echo "  • Internet connection"
            echo "  • Valid API keys in .env"
            ;;
        local)
            echo -e "${BLUE}━━━ Local Mode ━━━${NC}"
            echo "  • 100% offline operation"
            echo "  • All inference on local hardware"
            echo "  • No API keys or internet needed"
            echo "  • Cost: \$0 (just electricity)"
            echo ""
            echo -e "${YELLOW}Requirements:${NC}"
            echo "  • Pre-downloaded models in ./models/"
            echo "  • NVIDIA GPU with sufficient VRAM (24GB+ for 32B model)"
            echo ""
            local model_path
            model_path=$(get_local_model_path)
            if [[ -n "$model_path" ]]; then
                echo -e "${YELLOW}Local model configured:${NC} $model_path"
                echo -e "${YELLOW}Pre-download model:${NC}"
                echo "  huggingface-cli download $model_path --local-dir ./models/"
            else
                echo -e "${YELLOW}Pre-download models:${NC}"
                echo "  huggingface-cli download Qwen/Qwen2.5-32B-Instruct-AWQ --local-dir ./models/"
            fi
            ;;
        hybrid)
            echo -e "${BLUE}━━━ Hybrid Mode ━━━${NC}"
            echo "  • Local-first with automatic cloud fallback"
            echo "  • Best of both worlds: privacy + reliability"
            echo "  • Local vLLM as primary, cloud as backup"
            echo "  • Cost: \$0 when local works, cloud rates when fallback"
            echo ""
            echo -e "${YELLOW}Requirements:${NC}"
            echo "  • Local models downloaded"
            echo "  • API keys for fallback (optional but recommended)"
            echo ""
            echo -e "${YELLOW}Fallback triggers:${NC}"
            echo "  • Local model timeout (default: 30s)"
            echo "  • Local model error (5xx, connection refused)"
            echo "  • Empty/invalid response from local"
            ;;
    esac
    echo ""
}

#=============================================================================
# Commands
#=============================================================================

cmd_status() {
    local current=$(get_current_mode)
    
    echo -e "${BLUE}━━━ Dream Server Mode Status ━━━${NC}"
    echo ""
    echo -e "Current mode: ${BOLD}${current}${NC}"
    
    # Check compose file
    local compose_file="${DREAM_DIR}/docker-compose.${current}.yml"
    if [[ -f "$compose_file" ]]; then
        success "Compose file exists: docker-compose.${current}.yml"
    else
        warn "Compose file missing: docker-compose.${current}.yml"
    fi
    
    # Check running containers
    echo ""
    echo -e "${CYAN}Running containers:${NC}"
    cd "$DREAM_DIR"
    local docker_cmd
    docker_cmd=$(get_docker_compose_cmd)
    $docker_cmd -f "docker-compose.${current}.yml" ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || \
        docker-compose -f "docker-compose.${current}.yml" ps 2>/dev/null || \
        echo "  (no containers running)"
    
    print_mode_info "$current"
}

cmd_switch() {
    local new_mode=$1
    local current=$(get_current_mode)
    
    # Validate mode
    case "$new_mode" in
        cloud|local|hybrid) ;;
        *) error "Invalid mode: $new_mode. Use: cloud, local, or hybrid" ;;
    esac
    
    # Check compose file exists
    local compose_file="${DREAM_DIR}/docker-compose.${new_mode}.yml"
    if [[ ! -f "$compose_file" ]]; then
        error "Compose file not found: $compose_file"
    fi
    
    echo -e "${BLUE}━━━ Switching Dream Server Mode ━━━${NC}"
    echo ""
    echo -e "  From: ${YELLOW}${current}${NC}"
    echo -e "  To:   ${GREEN}${new_mode}${NC}"
    echo ""
    
    # Show warnings based on mode
    case "$new_mode" in
        local)
            warn "Local mode requires pre-downloaded models"
            warn "Web search will be disabled (requires internet)"
            echo ""
            ;;
        cloud)
            warn "Cloud mode requires valid API keys in .env"
            warn "All LLM requests will go to cloud providers"
            echo ""
            ;;
        hybrid)
            warn "Hybrid mode uses local first, cloud as fallback"
            warn "API keys optional but recommended for reliability"
            echo ""
            ;;
    esac
    
    # Prompt for confirmation (unless -y flag provided)
    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        read -p "Continue? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Cancelled"
            exit 0
        fi
    fi
    
    cd "$DREAM_DIR"
    
    # Stop current services
    log "Stopping current services..."
    local current_compose="${DREAM_DIR}/docker-compose.${current}.yml"
    local docker_cmd
    docker_cmd=$(get_docker_compose_cmd)
    if [[ -f "$current_compose" ]]; then
        $docker_cmd -f "$current_compose" down 2>/dev/null || true
    fi
    
    # Save new mode
    save_mode "$new_mode"
    
    # Start new services
    log "Starting ${new_mode} mode services..."
    $docker_cmd -f "$compose_file" up -d
    
    echo ""
    success "Mode switched to: ${new_mode}"
    echo ""
    
    # Wait and show status
    log "Waiting for services to start..."
    sleep 5
    
    echo ""
    echo -e "${CYAN}Service status:${NC}"
    docker_cmd=$(get_docker_compose_cmd)
    $docker_cmd -f "$compose_file" ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || \
        docker-compose -f "$compose_file" ps 2>/dev/null || true
    
    print_mode_info "$new_mode"
}

cmd_help() {
    cat << EOF
${BLUE}Dream Server Mode Switch${NC}
Part of M1 Zero-Cloud Initiative

${CYAN}Usage:${NC}
  mode-switch.sh <command>

${CYAN}Commands:${NC}
  cloud     Switch to cloud mode (full API access)
  local     Switch to local mode (100% offline)
  hybrid    Switch to hybrid mode (local-first + cloud fallback)
  status    Show current mode and service status
  help      Show this help

${CYAN}Modes:${NC}
  ${GREEN}cloud${NC}   - Uses LiteLLM gateway with cloud model access
            Requires API keys, internet connection
            Best quality, typical cloud costs
  
  ${GREEN}local${NC}   - 100% offline operation
            All inference on local hardware
            Requires pre-downloaded models
  
  ${GREEN}hybrid${NC}  - Local-first with automatic cloud fallback
            Tries local vLLM first, falls back to cloud on failure
            Best balance of privacy, speed, and reliability

${CYAN}Examples:${NC}
  ./mode-switch.sh status      # Check current mode
  ./mode-switch.sh cloud       # Switch to cloud mode
  ./mode-switch.sh local       # Switch to local mode
  ./mode-switch.sh hybrid      # Switch to hybrid mode

${CYAN}Data Safety:${NC}
  All modes share the same data volumes in ./data/
  Switching modes preserves all user data, conversations, etc.

EOF
}

#=============================================================================
# Main
#=============================================================================
cd "$DREAM_DIR"

# Handle -y flag for non-interactive mode
if [[ "$1" == "-y" ]]; then
    AUTO_CONFIRM="true"
    shift
fi

case "${1:-help}" in
    status|s)     cmd_status ;;
    cloud|c)      cmd_switch "cloud" ;;
    local|l)      cmd_switch "local" ;;
    hybrid|h)     cmd_switch "hybrid" ;;
    help|--help|-h) cmd_help ;;
    *)            error "Unknown command: $1. Run './mode-switch.sh help' for usage." ;;
esac
