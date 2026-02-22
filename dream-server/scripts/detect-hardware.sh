#!/bin/bash
# Dream Server Hardware Detection
# Detects GPU, CPU, RAM and recommends tier

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect OS and environment
detect_os() {
    if [[ -f /proc/version ]] && grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Detect NVIDIA GPU
detect_nvidia() {
    if command -v nvidia-smi &>/dev/null; then
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1
    fi
}

# Detect AMD GPU (ROCm)
detect_amd() {
    if command -v rocm-smi &>/dev/null; then
        rocm-smi --showproductname --showmeminfo vram 2>/dev/null | grep -E "GPU|Total Memory" | head -2
    fi
}

# Detect Apple Silicon
detect_apple() {
    if [[ "$(detect_os)" == "macos" ]]; then
        sysctl -n machdep.cpu.brand_string 2>/dev/null
        # Unified memory = system RAM on Apple Silicon
        sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024/1024)"GB unified"}'
    fi
}

# Get CPU info
detect_cpu() {
    local os=$(detect_os)
    case $os in
        macos)
            sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown"
            ;;
        *)
            grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs || echo "Unknown"
            ;;
    esac
}

# Get CPU cores
detect_cores() {
    local os=$(detect_os)
    case $os in
        macos)
            sysctl -n hw.ncpu 2>/dev/null || echo "0"
            ;;
        *)
            nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo "0"
            ;;
    esac
}

# Get RAM in GB
detect_ram() {
    local os=$(detect_os)
    case $os in
        macos)
            sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024/1024)}'
            ;;
        *)
            grep MemTotal /proc/meminfo 2>/dev/null | awk '{print int($2/1024/1024)}'
            ;;
    esac
}

# Parse VRAM from nvidia-smi output (in MB)
parse_nvidia_vram() {
    local output="$1"
    echo "$output" | awk -F',' '{gsub(/^ +| +$/,"",$2); print int($2)}'
}

# Determine tier based on VRAM
# T4: 48GB+ | T3: 20-47GB | T2: 12-19GB | T1: <12GB
get_tier() {
    local vram_mb=$1
    local vram_gb=$((vram_mb / 1024))
    
    if [[ $vram_gb -ge 48 ]]; then
        echo "T4"
    elif [[ $vram_gb -ge 20 ]]; then
        echo "T3"
    elif [[ $vram_gb -ge 12 ]]; then
        echo "T2"
    else
        echo "T1"
    fi
}

# Get tier description
tier_description() {
    case $1 in
        T4) echo "Ultimate (48GB+): Full 70B models, multi-model serving" ;;
        T3) echo "Pro (20-47GB): 32B models, comfortable headroom" ;;
        T2) echo "Starter (12-19GB): 7-14B models, lean configs" ;;
        T1) echo "Mini (<12GB): Small models or CPU inference" ;;
    esac
}

# Main detection
main() {
    local json_output=false
    [[ "$1" == "--json" ]] && json_output=true

    local os=$(detect_os)
    local cpu=$(detect_cpu)
    local cores=$(detect_cores)
    local ram=$(detect_ram)
    local gpu_name=""
    local gpu_vram_mb=0
    local gpu_type="none"
    
    # Try NVIDIA first
    local nvidia_out=$(detect_nvidia)
    if [[ -n "$nvidia_out" ]]; then
        gpu_name=$(echo "$nvidia_out" | awk -F',' '{gsub(/^ +| +$/,"",$1); print $1}')
        gpu_vram_mb=$(parse_nvidia_vram "$nvidia_out")
        gpu_type="nvidia"
    fi
    
    # Try AMD if no NVIDIA
    if [[ -z "$gpu_name" ]]; then
        local amd_out=$(detect_amd)
        if [[ -n "$amd_out" ]]; then
            gpu_name="AMD GPU (ROCm)"
            gpu_type="amd"
            # ROCm VRAM parsing would need work
        fi
    fi
    
    # Try Apple Silicon if macOS
    if [[ -z "$gpu_name" && "$os" == "macos" ]]; then
        local apple_out=$(detect_apple)
        if [[ -n "$apple_out" ]]; then
            gpu_name="Apple Silicon (Unified Memory)"
            gpu_vram_mb=$((ram * 1024))  # Use system RAM as "VRAM"
            gpu_type="apple"
        fi
    fi
    
    local tier=$(get_tier $gpu_vram_mb)
    local tier_desc=$(tier_description $tier)
    local gpu_vram_gb=$((gpu_vram_mb / 1024))
    
    if $json_output; then
        cat <<EOF
{
  "os": "$os",
  "cpu": "$cpu",
  "cores": $cores,
  "ram_gb": $ram,
  "gpu": {
    "type": "$gpu_type",
    "name": "$gpu_name",
    "vram_mb": $gpu_vram_mb,
    "vram_gb": $gpu_vram_gb
  },
  "tier": "$tier",
  "tier_description": "$tier_desc"
}
EOF
    else
        echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║      Dream Server Hardware Detection     ║${NC}"
        echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${GREEN}System:${NC}"
        echo "  OS:       $os"
        echo "  CPU:      $cpu"
        echo "  Cores:    $cores"
        echo "  RAM:      ${ram}GB"
        echo ""
        echo -e "${GREEN}GPU:${NC}"
        if [[ -n "$gpu_name" ]]; then
            echo "  Type:     $gpu_type"
            echo "  Name:     $gpu_name"
            echo "  VRAM:     ${gpu_vram_gb}GB"
        else
            echo "  No GPU detected (CPU-only mode)"
        fi
        echo ""
        echo -e "${YELLOW}Recommended Tier: ${tier}${NC}"
        echo "  $tier_desc"
        echo ""
    fi
}

main "$@"
