#!/bin/bash
#=============================================================================
# upgrade-model.sh — Atomic Model Upgrade with Rollback
#
# Part of Dream Server — Phase 0 Foundation
#
# Gracefully swaps models in vLLM with automatic rollback on failure.
# Ensures zero downtime when possible, minimal downtime otherwise.
#
# Usage:
#   ./upgrade-model.sh <new-model>           # Upgrade to new model
#   ./upgrade-model.sh --rollback            # Rollback to previous model
#   ./upgrade-model.sh --list                # List available models
#   ./upgrade-model.sh --current             # Show current model
#
#=============================================================================

set -euo pipefail

# Configuration
DREAM_DIR="${DREAM_DIR:-$HOME/.dream-server}"
MODELS_DIR="${MODELS_DIR:-$DREAM_DIR/models}"
STATE_FILE="$DREAM_DIR/model-state.json"
BACKUP_FILE="$DREAM_DIR/model-state.backup.json"
LOG_FILE="$DREAM_DIR/upgrade-model.log"

VLLM_HOST="${VLLM_HOST:-localhost}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_CONTAINER="${VLLM_CONTAINER:-dream-server-vllm-1}"

HEALTH_CHECK_TIMEOUT=120  # seconds
HEALTH_CHECK_INTERVAL=5   # seconds

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

#-----------------------------------------------------------------------------
# Utility Functions
#-----------------------------------------------------------------------------

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

ensure_dirs() {
    mkdir -p "$DREAM_DIR" "$MODELS_DIR"
    touch "$LOG_FILE"
}

#-----------------------------------------------------------------------------
# State Management
#-----------------------------------------------------------------------------

get_current_model() {
    if [[ -f "$STATE_FILE" ]]; then
        grep -o '"current": *"[^"]*"' "$STATE_FILE" | cut -d'"' -f4
    else
        echo ""
    fi
}

get_previous_model() {
    if [[ -f "$STATE_FILE" ]]; then
        grep -o '"previous": *"[^"]*"' "$STATE_FILE" | cut -d'"' -f4
    else
        echo ""
    fi
}

save_state() {
    local current="$1"
    local previous="$2"
    
    # Backup current state
    [[ -f "$STATE_FILE" ]] && cp "$STATE_FILE" "$BACKUP_FILE"
    
    cat > "$STATE_FILE" << EOF
{
    "current": "$current",
    "previous": "$previous",
    "updatedAt": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "history": [
        {"model": "$current", "activatedAt": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"}
    ]
}
EOF
}

#-----------------------------------------------------------------------------
# vLLM Operations
#-----------------------------------------------------------------------------

check_vllm_health() {
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        "http://${VLLM_HOST}:${VLLM_PORT}/health" 2>/dev/null || echo "000")
    [[ "$response" == "200" ]]
}

wait_for_vllm() {
    local timeout=$1
    local elapsed=0
    
    log "Waiting for vLLM to be ready (timeout: ${timeout}s)..."
    
    while [[ $elapsed -lt $timeout ]]; do
        if check_vllm_health; then
            success "vLLM is ready"
            return 0
        fi
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done
    
    echo ""
    error "vLLM health check timed out after ${timeout}s"
    return 1
}

test_inference() {
    log "Testing inference..."
    
    local response
    response=$(curl -s -X POST "http://${VLLM_HOST}:${VLLM_PORT}/v1/completions" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "default",
            "prompt": "Hello, I am",
            "max_tokens": 10
        }' 2>/dev/null || echo "")
    
    if echo "$response" | grep -q '"text"'; then
        success "Inference test passed"
        return 0
    else
        error "Inference test failed"
        echo "$response" >> "$LOG_FILE"
        return 1
    fi
}

stop_vllm() {
    log "Stopping vLLM..."
    
    if command -v docker &> /dev/null; then
        docker stop "$VLLM_CONTAINER" 2>/dev/null || true
        docker wait "$VLLM_CONTAINER" 2>/dev/null || true
    elif command -v dream &> /dev/null; then
        dream stop vllm 2>/dev/null || true
    else
        warn "Cannot stop vLLM: no docker or dream CLI found"
        return 1
    fi
    
    success "vLLM stopped"
}

start_vllm() {
    local model="$1"
    
    log "Starting vLLM with model: $model"
    
    # Update environment or compose file
    local env_file="$DREAM_DIR/.env"
    if [[ -f "$env_file" ]]; then
        # Update MODEL_PATH in .env
        if grep -q "^MODEL_PATH=" "$env_file"; then
            sed -i "s|^MODEL_PATH=.*|MODEL_PATH=$model|" "$env_file"
        else
            echo "MODEL_PATH=$model" >> "$env_file"
        fi
    fi
    
    if command -v docker &> /dev/null; then
        # Start via docker-compose
        local compose_file="$DREAM_DIR/docker-compose.yml"
        if [[ -f "$compose_file" ]]; then
            docker compose -f "$compose_file" up -d vllm
        else
            docker start "$VLLM_CONTAINER"
        fi
    elif command -v dream &> /dev/null; then
        dream start vllm
    else
        error "Cannot start vLLM: no docker or dream CLI found"
        return 1
    fi
}

#-----------------------------------------------------------------------------
# Main Commands
#-----------------------------------------------------------------------------

cmd_list() {
    echo -e "${CYAN}Available Models:${NC}"
    echo ""
    
    if [[ -d "$MODELS_DIR" ]]; then
        for model_dir in "$MODELS_DIR"/*/; do
            if [[ -f "${model_dir}config.json" ]]; then
                local model_name=$(basename "$model_dir")
                local size=$(du -sh "$model_dir" 2>/dev/null | cut -f1)
                local current=$(get_current_model)
                
                if [[ "$model_name" == "$current" ]]; then
                    echo -e "  ${GREEN}● $model_name${NC} ($size) [ACTIVE]"
                else
                    echo -e "  ○ $model_name ($size)"
                fi
            fi
        done
    else
        echo "  No models found in $MODELS_DIR"
    fi
    
    echo ""
    echo "Download more models with: model-bootstrap.sh"
}

cmd_current() {
    local current
    current=$(get_current_model)
    
    if [[ -n "$current" ]]; then
        echo -e "${CYAN}Current model:${NC} $current"
        
        if check_vllm_health; then
            echo -e "${GREEN}Status:${NC} Running"
        else
            echo -e "${RED}Status:${NC} Not responding"
        fi
    else
        echo "No model currently configured"
    fi
}

cmd_upgrade() {
    local new_model="$1"
    
    ensure_dirs
    
    # Validate new model exists
    local model_path="$MODELS_DIR/$new_model"
    if [[ ! -d "$model_path" ]] || [[ ! -f "$model_path/config.json" ]]; then
        # Maybe it's a full path?
        if [[ -d "$new_model" ]] && [[ -f "$new_model/config.json" ]]; then
            model_path="$new_model"
            new_model=$(basename "$new_model")
        else
            error "Model not found: $new_model"
            error "Available models:"
            cmd_list
            return 1
        fi
    fi
    
    local current_model
    current_model=$(get_current_model)
    
    if [[ "$current_model" == "$new_model" ]]; then
        warn "Model $new_model is already active"
        return 0
    fi
    
    log "Upgrading model: $current_model → $new_model"
    
    # Phase 1: Stop vLLM
    echo ""
    echo -e "${CYAN}Phase 1/4:${NC} Stopping vLLM..."
    stop_vllm || {
        error "Failed to stop vLLM"
        return 1
    }
    
    # Phase 2: Update configuration
    echo -e "${CYAN}Phase 2/4:${NC} Updating configuration..."
    save_state "$new_model" "$current_model"
    success "Configuration updated"
    
    # Phase 3: Start vLLM with new model
    echo -e "${CYAN}Phase 3/4:${NC} Starting vLLM with new model..."
    start_vllm "$model_path" || {
        error "Failed to start vLLM"
        warn "Attempting rollback..."
        cmd_rollback
        return 1
    }
    
    # Phase 4: Health check
    echo -e "${CYAN}Phase 4/4:${NC} Verifying health..."
    if wait_for_vllm $HEALTH_CHECK_TIMEOUT && test_inference; then
        echo ""
        success "Model upgrade complete!"
        echo -e "  Previous: ${YELLOW}$current_model${NC}"
        echo -e "  Current:  ${GREEN}$new_model${NC}"
        echo ""
        echo "Rollback available with: $0 --rollback"
    else
        error "Health check failed"
        warn "Attempting rollback..."
        cmd_rollback
        return 1
    fi
}

cmd_rollback() {
    local previous_model
    previous_model=$(get_previous_model)
    
    if [[ -z "$previous_model" ]]; then
        error "No previous model to rollback to"
        return 1
    fi
    
    local current_model
    current_model=$(get_current_model)
    
    log "Rolling back: $current_model → $previous_model"
    
    # Restore from backup state if available
    if [[ -f "$BACKUP_FILE" ]]; then
        cp "$BACKUP_FILE" "$STATE_FILE"
    fi
    
    local model_path="$MODELS_DIR/$previous_model"
    
    stop_vllm || true
    start_vllm "$model_path"
    
    if wait_for_vllm $HEALTH_CHECK_TIMEOUT && test_inference; then
        success "Rollback complete"
        save_state "$previous_model" "$current_model"
    else
        error "Rollback failed - manual intervention required"
        error "Check logs: $LOG_FILE"
        return 1
    fi
}

#-----------------------------------------------------------------------------
# Entry Point
#-----------------------------------------------------------------------------

main() {
    case "${1:-}" in
        --list|-l)
            cmd_list
            ;;
        --current|-c)
            cmd_current
            ;;
        --rollback|-r)
            cmd_rollback
            ;;
        --help|-h)
            cat << EOF
Dream Server Model Upgrade

Usage:
  $0 <model-name>        Upgrade to specified model
  $0 --list              List available models
  $0 --current           Show current model
  $0 --rollback          Rollback to previous model
  $0 --help              Show this help

Examples:
  $0 Qwen2.5-32B-Instruct-AWQ
  $0 /path/to/model
  $0 --rollback

Environment Variables:
  MODELS_DIR             Models directory (default: $MODELS_DIR)
  VLLM_HOST              vLLM hostname (default: localhost)
  VLLM_PORT              vLLM port (default: 8000)
  VLLM_CONTAINER         Docker container name (default: dream-server-vllm-1)

EOF
            ;;
        --*)
            error "Unknown option: $1"
            exit 1
            ;;
        "")
            error "Model name required"
            echo "Usage: $0 <model-name>"
            echo "       $0 --list"
            exit 1
            ;;
        *)
            cmd_upgrade "$1"
            ;;
    esac
}

main "$@"
