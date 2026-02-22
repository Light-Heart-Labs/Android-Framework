#!/bin/bash
# Dream Server Setup Wizard
# One-command installer for a complete local AI stack
# Usage: curl -fsSL https://dream.openclaw.ai/setup.sh | bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Source utility libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/lib/progress.sh" ]]; then
    source "$SCRIPT_DIR/lib/progress.sh"
fi
if [[ -f "$SCRIPT_DIR/lib/qrcode.sh" ]]; then
    source "$SCRIPT_DIR/lib/qrcode.sh"
fi

# Tier definitions
TIER_NANO="nano"      # 8GB RAM, no GPU — 1-3B models
TIER_EDGE="edge"      # 16GB RAM or 8GB VRAM — 7-8B models  
TIER_PRO="pro"        # 24GB+ VRAM — 32B models
TIER_CLUSTER="cluster" # Multi-GPU — 70B+ models

# ═══════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════

print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     ██████╗ ██████╗ ███████╗ █████╗ ███╗   ███╗           ║
    ║     ██╔══██╗██╔══██╗██╔════╝██╔══██╗████╗ ████║           ║
    ║     ██║  ██║██████╔╝█████╗  ███████║██╔████╔██║           ║
    ║     ██║  ██║██╔══██╗██╔══╝  ██╔══██║██║╚██╔╝██║           ║
    ║     ██████╔╝██║  ██║███████╗██║  ██║██║ ╚═╝ ██║           ║
    ║     ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝           ║
    ║              ███████╗███████╗██████╗ ██╗   ██╗            ║
    ║              ██╔════╝██╔════╝██╔══██╗██║   ██║            ║
    ║              ███████╗█████╗  ██████╔╝██║   ██║            ║
    ║              ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝            ║
    ║              ███████║███████╗██║  ██║ ╚████╔╝             ║
    ║              ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝              ║
    ║                                                           ║
    ║           Your AI. Your Hardware. Your Rules.             ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# ═══════════════════════════════════════════════════════════════
# HARDWARE DETECTION
# ═══════════════════════════════════════════════════════════════

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

detect_ram_gb() {
    local os=$(detect_os)
    if [[ "$os" == "linux" ]]; then
        awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo
    elif [[ "$os" == "macos" ]]; then
        sysctl -n hw.memsize | awk '{printf "%.0f", $1/1024/1024/1024}'
    else
        echo "0"
    fi
}

detect_gpu() {
    # Returns: nvidia|amd|apple|none
    local os=$(detect_os)
    
    if [[ "$os" == "macos" ]]; then
        # Check for Apple Silicon
        if sysctl -n machdep.cpu.brand_string 2>/dev/null | grep -qi "apple"; then
            echo "apple"
            return
        fi
    fi
    
    # Check for NVIDIA
    if command -v nvidia-smi &>/dev/null; then
        if nvidia-smi &>/dev/null; then
            echo "nvidia"
            return
        fi
    fi
    
    # Check for AMD ROCm
    if command -v rocm-smi &>/dev/null; then
        echo "amd"
        return
    fi
    
    echo "none"
}

detect_vram_gb() {
    local gpu=$(detect_gpu)
    
    case "$gpu" in
        nvidia)
            nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | awk '{printf "%.0f", $1/1024}'
            ;;
        apple)
            # Apple Silicon shares unified memory — report total RAM
            detect_ram_gb
            ;;
        amd)
            rocm-smi --showmeminfo vram 2>/dev/null | grep 'Total' | awk '{printf "%.0f", $3/1024/1024/1024}'
            ;;
        *)
            echo "0"
            ;;
    esac
}

detect_gpu_count() {
    local gpu=$(detect_gpu)
    
    case "$gpu" in
        nvidia)
            nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | wc -l
            ;;
        apple)
            echo "1"  # Apple Silicon is unified
            ;;
        amd)
            rocm-smi --showid 2>/dev/null | grep 'GPU' | wc -l
            ;;
        *)
            echo "0"
            ;;
    esac
}

detect_cpu_cores() {
    local os=$(detect_os)
    if [[ "$os" == "linux" ]]; then
        nproc 2>/dev/null || echo "4"
    elif [[ "$os" == "macos" ]]; then
        sysctl -n hw.ncpu 2>/dev/null || echo "4"
    else
        echo "4"
    fi
}

detect_disk_free_gb() {
    local target_dir="${1:-$HOME}"
    df -BG "$target_dir" 2>/dev/null | tail -1 | awk '{gsub(/G/,""); print $4}'
}

# ═══════════════════════════════════════════════════════════════
# TIER SELECTION
# ═══════════════════════════════════════════════════════════════

recommend_tier() {
    local ram_gb=$1
    local vram_gb=$2
    local gpu_count=$3
    
    # Multi-GPU → Cluster
    if [[ $gpu_count -gt 1 ]] && [[ $vram_gb -ge 20 ]]; then
        echo "$TIER_CLUSTER"
        return
    fi
    
    # High VRAM → Pro
    if [[ $vram_gb -ge 20 ]]; then
        echo "$TIER_PRO"
        return
    fi
    
    # Medium VRAM or good RAM → Edge
    if [[ $vram_gb -ge 8 ]] || [[ $ram_gb -ge 16 ]]; then
        echo "$TIER_EDGE"
        return
    fi
    
    # Fallback → Nano
    echo "$TIER_NANO"
}

tier_description() {
    local tier=$1
    case "$tier" in
        nano)
            echo "Nano (1-3B models) — Good for: simple chat, summarization"
            ;;
        edge)
            echo "Edge (7-8B models) — Good for: coding, reasoning, general use"
            ;;
        pro)
            echo "Pro (32B models) — Good for: complex tasks, tool use, agents"
            ;;
        cluster)
            echo "Cluster (70B+ models) — Good for: everything, enterprise scale"
            ;;
    esac
}

tier_model() {
    local tier=$1
    case "$tier" in
        nano)
            echo "Qwen2.5-1.5B-Instruct"
            ;;
        edge)
            echo "Qwen2.5-7B-Instruct-AWQ"
            ;;
        pro)
            echo "Qwen2.5-32B-Instruct-AWQ"
            ;;
        cluster)
            echo "Qwen2.5-72B-Instruct-AWQ"
            ;;
    esac
}

tier_model_size_gb() {
    local tier=$1
    case "$tier" in
        nano) echo "2" ;;
        edge) echo "5" ;;
        pro) echo "18" ;;
        cluster) echo "40" ;;
    esac
}

# ═══════════════════════════════════════════════════════════════
# DEPENDENCY CHECKS
# ═══════════════════════════════════════════════════════════════

check_docker() {
    if ! command -v docker &>/dev/null; then
        return 1
    fi
    if ! docker info &>/dev/null; then
        return 2  # Docker exists but not running/accessible
    fi
    return 0
}

check_nvidia_docker() {
    if ! docker info 2>/dev/null | grep -q "nvidia"; then
        # Try explicit check
        if ! docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi &>/dev/null 2>&1; then
            return 1
        fi
    fi
    return 0
}

install_docker() {
    local os=$(detect_os)
    echo -e "${YELLOW}Installing Docker...${NC}"
    
    if [[ "$os" == "linux" ]]; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker "$USER"
        echo -e "${GREEN}Docker installed. You may need to log out and back in.${NC}"
    elif [[ "$os" == "macos" ]]; then
        echo -e "${YELLOW}Please install Docker Desktop from: https://docker.com/products/docker-desktop${NC}"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════
# TUI COMPONENTS
# ═══════════════════════════════════════════════════════════════

print_section() {
    echo -e "\n${BOLD}${BLUE}═══ $1 ═══${NC}\n"
}

print_check() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
}

print_info() {
    echo -e "  ${CYAN}ℹ${NC} $1"
}

confirm() {
    local prompt="$1"
    local default="${2:-y}"
    
    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n] "
    else
        prompt="$prompt [y/N] "
    fi
    
    read -p "$prompt" response
    response=${response:-$default}
    
    [[ "$response" =~ ^[Yy]$ ]]
}

select_tier() {
    local recommended=$1
    
    echo -e "\n${BOLD}Available tiers:${NC}\n"
    echo -e "  ${CYAN}1)${NC} $(tier_description nano)"
    echo -e "  ${CYAN}2)${NC} $(tier_description edge)"
    echo -e "  ${CYAN}3)${NC} $(tier_description pro)"
    echo -e "  ${CYAN}4)${NC} $(tier_description cluster)"
    
    echo ""
    
    local default_num
    case "$recommended" in
        nano) default_num=1 ;;
        edge) default_num=2 ;;
        pro) default_num=3 ;;
        cluster) default_num=4 ;;
    esac
    
    read -p "Select tier [$default_num]: " choice
    choice=${choice:-$default_num}
    
    case "$choice" in
        1) echo "$TIER_NANO" ;;
        2) echo "$TIER_EDGE" ;;
        3) echo "$TIER_PRO" ;;
        4) echo "$TIER_CLUSTER" ;;
        *) echo "$recommended" ;;
    esac
}

# ═══════════════════════════════════════════════════════════════
# MAIN WIZARD
# ═══════════════════════════════════════════════════════════════

main() {
    print_banner
    
    print_section "Hardware Detection"
    
    local os=$(detect_os)
    local ram_gb=$(detect_ram_gb)
    local gpu=$(detect_gpu)
    local vram_gb=$(detect_vram_gb)
    local gpu_count=$(detect_gpu_count)
    local cpu_cores=$(detect_cpu_cores)
    local disk_free=$(detect_disk_free_gb "$HOME")
    
    echo -e "  ${BOLD}System:${NC} $os"
    echo -e "  ${BOLD}RAM:${NC} ${ram_gb}GB"
    echo -e "  ${BOLD}CPU Cores:${NC} $cpu_cores"
    echo -e "  ${BOLD}GPU:${NC} $gpu ($gpu_count GPU(s), ${vram_gb}GB VRAM)"
    echo -e "  ${BOLD}Free Disk:${NC} ${disk_free}GB"
    
    # Recommend tier
    local recommended=$(recommend_tier "$ram_gb" "$vram_gb" "$gpu_count")
    echo -e "\n  ${GREEN}Recommended tier:${NC} $(tier_description $recommended)"
    
    print_section "Tier Selection"
    
    local selected_tier=$(select_tier "$recommended")
    local model=$(tier_model "$selected_tier")
    local model_size=$(tier_model_size_gb "$selected_tier")
    
    echo -e "\n  Selected: ${BOLD}$(tier_description $selected_tier)${NC}"
    echo -e "  Model: ${CYAN}$model${NC} (~${model_size}GB)"
    
    # Check disk space
    if [[ $disk_free -lt $((model_size + 10)) ]]; then
        print_error "Not enough disk space. Need ~$((model_size + 10))GB, have ${disk_free}GB"
        exit 1
    fi
    
    print_section "Dependency Check"
    
    # Docker
    if check_docker; then
        print_check "Docker installed and running"
    else
        print_warn "Docker not found or not running"
        if confirm "Install Docker?"; then
            install_docker || exit 1
        else
            print_error "Docker is required"
            exit 1
        fi
    fi
    
    # NVIDIA Docker (if NVIDIA GPU)
    if [[ "$gpu" == "nvidia" ]]; then
        if check_nvidia_docker; then
            print_check "NVIDIA Container Toolkit installed"
        else
            print_warn "NVIDIA Container Toolkit not found"
            echo -e "  ${YELLOW}Install with: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html${NC}"
        fi
    fi
    
    print_section "Installation"
    
    # Initialize time estimates for selected tier
    if type init_phase_estimates &>/dev/null; then
        init_phase_estimates "$selected_tier"
        local total_estimate=$((${PHASE_ESTIMATES[docker_pull]:-0} + ${PHASE_ESTIMATES[model_download]:-0} + ${PHASE_ESTIMATES[startup]:-0}))
        local total_duration=$(format_duration $total_estimate)
        echo -e "  ${CYAN}Estimated total time: ~$total_duration${NC}"
    fi
    
    local install_dir="${DREAM_SERVER_DIR:-$HOME/dream-server}"
    read -p "Install directory [$install_dir]: " custom_dir
    install_dir="${custom_dir:-$install_dir}"
    
    echo -e "\n${BOLD}Ready to install:${NC}"
    echo -e "  • Directory: $install_dir"
    echo -e "  • Tier: $selected_tier"
    echo -e "  • Model: $model"
    echo -e "  • Download size: ~${model_size}GB"
    
    if ! confirm "\nProceed with installation?"; then
        echo -e "${YELLOW}Installation cancelled.${NC}"
        exit 0
    fi
    
    # Create directory
    mkdir -p "$install_dir"
    cd "$install_dir"
    
    # Export config for docker-compose
    cat > .env << EOF
DREAM_TIER=$selected_tier
DREAM_MODEL=$model
DREAM_GPU=$gpu
DREAM_VRAM=$vram_gb
EOF
    
    print_check "Configuration saved"
    
    # Select compose file based on tier
    echo -e "\n${CYAN}Selecting compose configuration...${NC}"
    
    local compose_file
    case "$selected_tier" in
        nano|edge)
            compose_file="docker-compose.edge.yml"
            echo -e "  ${BLUE}→ Using edge configuration (Ollama + Piper)${NC}"
            ;;
        pro)
            compose_file="docker-compose.yml"
            echo -e "  ${BLUE}→ Using pro configuration (vLLM + Kokoro)${NC}"
            ;;
        cluster)
            compose_file="docker-compose.yml"
            echo -e "  ${BLUE}→ Using cluster configuration (vLLM + multi-GPU)${NC}"
            ;;
        *)
            compose_file="docker-compose.yml"
            ;;
    esac
    
    # Verify compose file exists
    if [[ ! -f "$SCRIPT_DIR/$compose_file" ]]; then
        echo -e "${YELLOW}⚠ Compose file not found locally. Downloading...${NC}"
        curl -fsSL "https://raw.githubusercontent.com/Light-Heart-Labs/Lighthouse-AI/main/dream-server/$compose_file" -o "$SCRIPT_DIR/$compose_file" || {
            echo -e "${RED}✗ Failed to download compose file${NC}"
            exit 1
        }
    fi
    
    # Export for later use
    export COMPOSE_FILE="$SCRIPT_DIR/$compose_file"
    
    print_check "Compose file ready: $compose_file"
    
    # Pull images
    if type print_phase &>/dev/null; then
        print_phase "docker_pull" "Pulling Docker images"
    else
        echo -e "\n${CYAN}Pulling Docker images (this may take a while)...${NC}"
    fi
    
    if type docker_pull_with_progress &>/dev/null; then
        docker_pull_with_progress "$COMPOSE_FILE" 2>/dev/null || true
    else
        docker compose -f "$COMPOSE_FILE" pull 2>/dev/null || true
    fi
    
    print_check "Images pulled"
    
    # Start services
    echo -e "\n${CYAN}Starting services...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d 2>/dev/null || {
        echo -e "${YELLOW}⚠ Failed to start services. Run manually:${NC}"
        echo -e "  docker compose -f $compose_file up -d"
    }
    
    print_section "Setup Complete!"
    
    # Use fancy success card if available
    if type print_success_card &>/dev/null; then
        print_success_card "$selected_tier" "$model" "http://localhost:3001" "http://localhost:8000/v1"
    else
        echo -e "${GREEN}Dream Server is starting up!${NC}\n"
        echo -e "  ${BOLD}Dashboard:${NC} http://localhost:3001"
        echo -e "  ${BOLD}API:${NC} http://localhost:8000/v1"
        echo -e "  ${BOLD}Voice:${NC} http://localhost:3001/voice"
        echo ""
    fi
    
    echo -e "  ${CYAN}First startup downloads the model (~${model_size}GB).${NC}"
    echo -e "  ${CYAN}Monitor progress: docker compose logs -f${NC}"
    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    echo -e "  1. Wait for model download to complete"
    echo -e "  2. Open the Dashboard URL in your browser"
    echo -e "  3. Start chatting!"
    echo ""
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
