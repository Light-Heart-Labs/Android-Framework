#!/bin/bash
#=============================================================================
# model-bootstrap.sh — Background Model Download with Progress Tracking
#
# Part of Dream Server — Phase 0 Foundation
#
# Downloads the full model in the background while a lightweight bootstrap
# model serves requests. Tracks progress for Dashboard display.
#
# Usage:
#   ./model-bootstrap.sh                    # Interactive
#   ./model-bootstrap.sh --background       # Daemon mode (no output)
#   ./model-bootstrap.sh --status           # Check download status
#   ./model-bootstrap.sh --cancel           # Cancel active download
#
# Progress file: ~/.dream-server/bootstrap-status.json
#=============================================================================

set -euo pipefail

# Configuration
DREAM_DIR="${DREAM_DIR:-$HOME/.dream-server}"
STATUS_FILE="$DREAM_DIR/bootstrap-status.json"
PID_FILE="$DREAM_DIR/bootstrap.pid"
LOG_FILE="$DREAM_DIR/bootstrap.log"
MODELS_DIR="${MODELS_DIR:-$DREAM_DIR/models}"

# Default models (can be overridden via env)
BOOTSTRAP_MODEL="${BOOTSTRAP_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
FULL_MODEL="${FULL_MODEL:-Qwen/Qwen2.5-32B-Instruct-AWQ}"

# Retry configuration
MAX_RETRIES=3
RETRY_DELAYS=(2 8 32)  # Exponential backoff: 2s, 8s, 32s
DOWNLOAD_TIMEOUT=7200  # 2 hours max

# Colors (disabled in background mode)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

BACKGROUND=false
QUIET=false

#-----------------------------------------------------------------------------
# Utility Functions
#-----------------------------------------------------------------------------

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    if [[ "$BACKGROUND" == "true" ]]; then
        echo "$msg" >> "$LOG_FILE"
    elif [[ "$QUIET" != "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

success() {
    if [[ "$BACKGROUND" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >> "$LOG_FILE"
    elif [[ "$QUIET" != "true" ]]; then
        echo -e "${GREEN}[OK]${NC} $1"
    fi
}

warn() {
    if [[ "$BACKGROUND" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1" >> "$LOG_FILE"
    elif [[ "$QUIET" != "true" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

error() {
    if [[ "$BACKGROUND" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
    else
        echo -e "${RED}[ERROR]${NC} $1" >&2
    fi
}

ensure_dirs() {
    mkdir -p "$DREAM_DIR" "$MODELS_DIR"
}

#-----------------------------------------------------------------------------
# Status File Management
#-----------------------------------------------------------------------------

write_status() {
    local status="$1"
    local percent="${2:-0}"
    local bytes_downloaded="${3:-0}"
    local bytes_total="${4:-0}"
    local speed="${5:-0}"
    local eta="${6:-}"
    local error_msg="${7:-}"
    
    cat > "$STATUS_FILE" << EOF
{
    "status": "$status",
    "model": "$FULL_MODEL",
    "bootstrapModel": "$BOOTSTRAP_MODEL",
    "percent": $percent,
    "bytesDownloaded": $bytes_downloaded,
    "bytesTotal": $bytes_total,
    "speedBytesPerSec": $speed,
    "eta": "$eta",
    "error": "$error_msg",
    "startedAt": "${STARTED_AT:-}",
    "updatedAt": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "pid": $$
}
EOF
}

read_status() {
    if [[ -f "$STATUS_FILE" ]]; then
        cat "$STATUS_FILE"
    else
        echo '{"status": "none"}'
    fi
}

#-----------------------------------------------------------------------------
# Model Download with Progress
#-----------------------------------------------------------------------------

get_model_size() {
    local model="$1"
    # Query HuggingFace API for model size
    local api_url="https://huggingface.co/api/models/${model}"
    local size
    size=$(curl -s "$api_url" | grep -o '"size":[0-9]*' | head -1 | cut -d: -f2)
    echo "${size:-0}"
}

download_model() {
    local model="$1"
    local target_dir="$2"
    local attempt=1
    
    STARTED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    
    # Get expected size
    local total_size
    total_size=$(get_model_size "$model")
    
    log "Downloading model: $model"
    log "Target directory: $target_dir"
    [[ "$total_size" -gt 0 ]] && log "Expected size: $(numfmt --to=iec-i --suffix=B $total_size 2>/dev/null || echo "$total_size bytes")"
    
    while [[ $attempt -le $MAX_RETRIES ]]; do
        log "Download attempt $attempt of $MAX_RETRIES"
        write_status "downloading" 0 0 "$total_size" 0 "calculating..."
        
        # Use huggingface-cli if available, otherwise fallback to git lfs
        if command -v huggingface-cli &> /dev/null; then
            download_with_hf_cli "$model" "$target_dir" "$total_size" && return 0
        else
            download_with_git_lfs "$model" "$target_dir" "$total_size" && return 0
        fi
        
        # Download failed, retry with backoff
        if [[ $attempt -lt $MAX_RETRIES ]]; then
            local delay=${RETRY_DELAYS[$((attempt-1))]}
            warn "Download failed, retrying in ${delay}s..."
            write_status "retrying" 0 0 "$total_size" 0 "" "Attempt $attempt failed, retrying in ${delay}s"
            sleep "$delay"
        fi
        
        ((attempt++))
    done
    
    error "Download failed after $MAX_RETRIES attempts"
    write_status "failed" 0 0 "$total_size" 0 "" "Download failed after $MAX_RETRIES attempts"
    return 1
}

download_with_hf_cli() {
    local model="$1"
    local target_dir="$2"
    local total_size="$3"
    
    # Create a named pipe for progress monitoring
    local progress_pipe=$(mktemp -u)
    mkfifo "$progress_pipe"
    
    # Monitor progress in background
    (
        local last_size=0
        local last_time=$(date +%s)
        
        while true; do
            sleep 5
            
            # Calculate current download size
            local current_size=0
            if [[ -d "$target_dir" ]]; then
                current_size=$(du -sb "$target_dir" 2>/dev/null | cut -f1 || echo 0)
            fi
            
            # Calculate speed
            local now=$(date +%s)
            local elapsed=$((now - last_time))
            local speed=0
            if [[ $elapsed -gt 0 ]]; then
                speed=$(( (current_size - last_size) / elapsed ))
            fi
            
            # Calculate percentage and ETA
            local percent=0
            local eta="unknown"
            if [[ "$total_size" -gt 0 ]]; then
                percent=$(( (current_size * 100) / total_size ))
                if [[ $speed -gt 0 ]]; then
                    local remaining=$((total_size - current_size))
                    local eta_secs=$((remaining / speed))
                    eta=$(printf '%02d:%02d:%02d' $((eta_secs/3600)) $(((eta_secs%3600)/60)) $((eta_secs%60)))
                fi
            fi
            
            write_status "downloading" "$percent" "$current_size" "$total_size" "$speed" "$eta"
            
            last_size=$current_size
            last_time=$now
            
            # Check if download process is still running
            if ! kill -0 $$ 2>/dev/null; then
                break
            fi
        done
    ) &
    local monitor_pid=$!
    
    # Run the actual download
    local result=0
    huggingface-cli download "$model" \
        --local-dir "$target_dir" \
        --local-dir-use-symlinks False \
        --resume-download \
        2>> "$LOG_FILE" || result=$?
    
    # Stop the monitor
    kill $monitor_pid 2>/dev/null || true
    rm -f "$progress_pipe"
    
    return $result
}

download_with_git_lfs() {
    local model="$1"
    local target_dir="$2"
    local total_size="$3"
    
    log "Using git-lfs for download (huggingface-cli not found)"
    
    # Clone with git lfs
    local repo_url="https://huggingface.co/${model}"
    
    GIT_LFS_SKIP_SMUDGE=1 git clone "$repo_url" "$target_dir" 2>> "$LOG_FILE" || return 1
    
    cd "$target_dir"
    git lfs pull 2>> "$LOG_FILE" || return 1
    
    return 0
}

#-----------------------------------------------------------------------------
# vLLM Hot-Swap
#-----------------------------------------------------------------------------

notify_vllm_model_ready() {
    local model_path="$1"
    
    log "Notifying vLLM that new model is ready..."
    
    # Check if vLLM supports hot-swap API
    local vllm_host="${VLLM_HOST:-localhost}"
    local vllm_port="${VLLM_PORT:-8000}"
    
    # Try the model loading API (if available in vLLM version)
    local response
    response=$(curl -s -X POST "http://${vllm_host}:${vllm_port}/v1/models/load" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"$model_path\"}" 2>/dev/null || echo "")
    
    if [[ -n "$response" ]] && echo "$response" | grep -q '"success"'; then
        success "vLLM hot-swap successful"
        return 0
    else
        warn "vLLM hot-swap not available, manual restart required"
        warn "Run: dream restart vllm"
        return 1
    fi
}

#-----------------------------------------------------------------------------
# Main Commands
#-----------------------------------------------------------------------------

cmd_status() {
    local status
    status=$(read_status)
    
    if [[ "$1" == "--json" ]]; then
        echo "$status"
        return
    fi
    
    local current_status
    current_status=$(echo "$status" | grep -o '"status": *"[^"]*"' | cut -d'"' -f4)
    
    case "$current_status" in
        none)
            echo "No bootstrap in progress"
            ;;
        downloading)
            local percent model eta
            percent=$(echo "$status" | grep -o '"percent": *[0-9]*' | grep -o '[0-9]*')
            model=$(echo "$status" | grep -o '"model": *"[^"]*"' | cut -d'"' -f4)
            eta=$(echo "$status" | grep -o '"eta": *"[^"]*"' | cut -d'"' -f4)
            echo -e "${CYAN}Downloading:${NC} $model"
            echo -e "${CYAN}Progress:${NC} ${percent}%"
            echo -e "${CYAN}ETA:${NC} $eta"
            ;;
        completed)
            echo -e "${GREEN}Bootstrap complete!${NC} Full model ready."
            ;;
        failed)
            local err
            err=$(echo "$status" | grep -o '"error": *"[^"]*"' | cut -d'"' -f4)
            echo -e "${RED}Bootstrap failed:${NC} $err"
            ;;
        *)
            echo "Status: $current_status"
            ;;
    esac
}

cmd_cancel() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Cancelling bootstrap download (PID: $pid)"
            kill "$pid"
            write_status "cancelled" 0 0 0 0 "" "Cancelled by user"
            rm -f "$PID_FILE"
            success "Download cancelled"
        else
            warn "No active download found"
            rm -f "$PID_FILE"
        fi
    else
        warn "No active download found"
    fi
}

cmd_download() {
    ensure_dirs
    
    # Check if already downloading
    if [[ -f "$PID_FILE" ]]; then
        local existing_pid
        existing_pid=$(cat "$PID_FILE")
        if kill -0 "$existing_pid" 2>/dev/null; then
            error "Download already in progress (PID: $existing_pid)"
            error "Use --cancel to stop it, or --status to check progress"
            return 1
        fi
    fi
    
    # Save PID
    echo $$ > "$PID_FILE"
    
    # Trap to clean up on exit
    trap 'rm -f "$PID_FILE"' EXIT
    
    local target_dir="$MODELS_DIR/$(basename "$FULL_MODEL")"
    
    if [[ -d "$target_dir" ]] && [[ -f "$target_dir/config.json" ]]; then
        success "Model already downloaded: $target_dir"
        write_status "completed" 100 0 0 0 ""
        return 0
    fi
    
    # Start download
    if download_model "$FULL_MODEL" "$target_dir"; then
        success "Model download complete!"
        write_status "completed" 100 0 0 0 ""
        
        # Try hot-swap
        notify_vllm_model_ready "$target_dir" || true
        
        return 0
    else
        return 1
    fi
}

#-----------------------------------------------------------------------------
# Entry Point
#-----------------------------------------------------------------------------

main() {
    case "${1:-}" in
        --status|-s)
            cmd_status "${2:-}"
            ;;
        --cancel|-c)
            cmd_cancel
            ;;
        --background|-b)
            BACKGROUND=true
            shift
            cmd_download "$@" &
            disown
            echo "Bootstrap started in background. Check progress with: $0 --status"
            ;;
        --help|-h)
            cat << EOF
Dream Server Model Bootstrap

Usage:
  $0                     Start download (interactive)
  $0 --background        Start download in background
  $0 --status            Check download progress
  $0 --status --json     Get status as JSON (for Dashboard)
  $0 --cancel            Cancel active download

Environment Variables:
  FULL_MODEL             Model to download (default: $FULL_MODEL)
  BOOTSTRAP_MODEL        Lightweight model for immediate use (default: $BOOTSTRAP_MODEL)
  MODELS_DIR             Where to store models (default: $MODELS_DIR)
  VLLM_HOST              vLLM hostname for hot-swap (default: localhost)
  VLLM_PORT              vLLM port for hot-swap (default: 8000)

Progress File:
  $STATUS_FILE

EOF
            ;;
        *)
            cmd_download "$@"
            ;;
    esac
}

main "$@"
