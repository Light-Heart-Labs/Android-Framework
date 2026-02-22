#!/usr/bin/env bash
# ============================================================
# Dream Server — Clean Test Install Script
# Removes all artifacts from a previous install so install.sh
# can be tested from scratch on the same machine.
#
# Levels:
#   (default)   Remove Dream Server artifacts only
#   --full      Also remove ALL Docker images/cache and
#               uninstall Docker, Docker Compose, and
#               NVIDIA Container Toolkit
# ============================================================
set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="${INSTALL_DIR:-$HOME/dream-server}"
FULL_CLEAN=false
AUTO_YES=false

for arg in "$@"; do
    case "$arg" in
        --full)     FULL_CLEAN=true ;;
        --yes|-y)   AUTO_YES=true ;;
    esac
done

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Dream Server — Clean Test Install          ║${NC}"
if $FULL_CLEAN; then
echo -e "${CYAN}║   FULL MODE: dependencies will be removed   ║${NC}"
else
echo -e "${CYAN}║   Removes all artifacts for fresh test       ║${NC}"
fi
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Scan phase ──────────────────────────────────────────────
echo -e "${YELLOW}Scanning for Dream Server artifacts...${NC}"
echo ""

FOUND=0

# 1. Running containers
CONTAINERS=$(docker ps -a --filter "name=dream-" --format "{{.Names}}" 2>/dev/null || true)
if [[ -n "$CONTAINERS" ]]; then
    echo -e "  ${CYAN}Containers:${NC}"
    echo "$CONTAINERS" | sed 's/^/    /'
    FOUND=1
else
    echo -e "  ${GREEN}Containers:${NC} none"
fi

# 2. Docker images (dream-specific)
IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" 2>/dev/null | grep -E 'dream-server|dream-livekit' || true)
if [[ -n "$IMAGES" ]]; then
    echo -e "  ${CYAN}Images:${NC}"
    echo "$IMAGES" | sed 's/^/    /'
    FOUND=1
else
    echo -e "  ${GREEN}Images:${NC} none"
fi

# 2b. ALL Docker images (for --full mode display)
ALL_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}} ({{.Size}})" 2>/dev/null || true)
ALL_IMAGE_COUNT=$(docker images -q 2>/dev/null | wc -l || echo 0)
if $FULL_CLEAN && [[ "$ALL_IMAGE_COUNT" -gt 0 ]]; then
    DOCKER_DISK=$(docker system df --format "{{.Size}}" 2>/dev/null | head -1 || echo "unknown")
    echo -e "  ${CYAN}All Docker images:${NC} ${ALL_IMAGE_COUNT} images (${DOCKER_DISK})"
    FOUND=1
fi

# 3. Docker volumes
VOLUMES=$(docker volume ls --format "{{.Name}}" 2>/dev/null | grep -i dream || true)
if [[ -n "$VOLUMES" ]]; then
    echo -e "  ${CYAN}Volumes:${NC}"
    echo "$VOLUMES" | sed 's/^/    /'
    FOUND=1
else
    echo -e "  ${GREEN}Volumes:${NC} none"
fi

# 4. Install directory
if [[ -d "$INSTALL_DIR" ]]; then
    SIZE=$(du -sh "$INSTALL_DIR" 2>/dev/null | cut -f1)
    echo -e "  ${CYAN}Install dir:${NC} $INSTALL_DIR ($SIZE)"
    FOUND=1
else
    echo -e "  ${GREEN}Install dir:${NC} not found"
fi

# 5. Desktop shortcut
DESKTOP_FILE="$HOME/.local/share/applications/dream-server.desktop"
if [[ -f "$DESKTOP_FILE" ]]; then
    echo -e "  ${CYAN}Desktop shortcut:${NC} $DESKTOP_FILE"
    FOUND=1
else
    echo -e "  ${GREEN}Desktop shortcut:${NC} none"
fi

# 6. GNOME favorites
FAVORITES=$(gsettings get org.gnome.shell favorite-apps 2>/dev/null || echo "[]")
if echo "$FAVORITES" | grep -q "dream-server"; then
    echo -e "  ${CYAN}GNOME sidebar:${NC} pinned"
    FOUND=1
else
    echo -e "  ${GREEN}GNOME sidebar:${NC} not pinned"
fi

# 7. Docker network
NETWORKS=$(docker network ls --format "{{.Name}}" 2>/dev/null | grep -i dream || true)
if [[ -n "$NETWORKS" ]]; then
    echo -e "  ${CYAN}Networks:${NC}"
    echo "$NETWORKS" | sed 's/^/    /'
    FOUND=1
else
    echo -e "  ${GREEN}Networks:${NC} none"
fi

# 8. Systemd services (if any)
SERVICES=$(systemctl --user list-units --all 2>/dev/null | grep -i dream | awk '{print $1}' || true)
if [[ -n "$SERVICES" ]]; then
    echo -e "  ${CYAN}Systemd services:${NC}"
    echo "$SERVICES" | sed 's/^/    /'
    FOUND=1
else
    echo -e "  ${GREEN}Systemd services:${NC} none"
fi

# 9. Dependencies (--full mode)
if $FULL_CLEAN; then
    echo ""
    echo -e "${YELLOW}Scanning installer dependencies...${NC}"
    echo ""

    HAS_DOCKER=false
    HAS_COMPOSE=false
    HAS_NVIDIA_CTK=false

    if command -v docker &>/dev/null; then
        DOCKER_VER=$(docker --version 2>/dev/null | head -1)
        echo -e "  ${CYAN}Docker:${NC} $DOCKER_VER"
        HAS_DOCKER=true
        FOUND=1
    else
        echo -e "  ${GREEN}Docker:${NC} not installed"
    fi

    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_VER=$(docker compose version 2>/dev/null | head -1)
        echo -e "  ${CYAN}Docker Compose:${NC} $COMPOSE_VER"
        HAS_COMPOSE=true
        FOUND=1
    else
        echo -e "  ${GREEN}Docker Compose:${NC} not installed"
    fi

    if dpkg -l nvidia-container-toolkit &>/dev/null 2>&1 || command -v nvidia-ctk &>/dev/null; then
        CTK_VER=$(nvidia-ctk --version 2>/dev/null | head -1 || echo "installed")
        echo -e "  ${CYAN}NVIDIA Container Toolkit:${NC} $CTK_VER"
        HAS_NVIDIA_CTK=true
        FOUND=1
    else
        echo -e "  ${GREEN}NVIDIA Container Toolkit:${NC} not installed"
    fi
fi

echo ""

if [[ "$FOUND" -eq 0 ]]; then
    echo -e "${GREEN}No Dream Server artifacts found. Machine is clean.${NC}"
    exit 0
fi

# ── Confirmation ────────────────────────────────────────────
if ! $AUTO_YES; then
    echo -e "${RED}This will REMOVE everything listed above.${NC}"
    if $FULL_CLEAN; then
        echo -e "${RED}INCLUDING Docker, Docker Compose, and NVIDIA Container Toolkit.${NC}"
    fi
    echo -e "${YELLOW}Models in $INSTALL_DIR/models/ will be PRESERVED (moved to /tmp/dream-models-backup).${NC}"
    echo ""
    read -p "Proceed? [y/N] " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}Cleaning...${NC}"

# ── Remove phase ────────────────────────────────────────────

# 1. Stop and remove containers
if [[ -n "$CONTAINERS" ]]; then
    echo -n "  Stopping containers... "
    # Use compose if compose file exists, otherwise docker rm
    if [[ -f "$INSTALL_DIR/docker-compose.yml" ]]; then
        (cd "$INSTALL_DIR" && docker compose --profile openclaw --profile voice --profile workflows --profile rag --profile multi-model down --remove-orphans 2>/dev/null) || true
    fi
    # Force remove any stragglers
    docker rm -f $CONTAINERS 2>/dev/null || true
    echo -e "${GREEN}done${NC}"
fi

# 2. Remove dream-specific images
if [[ -n "$IMAGES" ]]; then
    echo -n "  Removing Dream Server images... "
    echo "$IMAGES" | xargs docker rmi -f 2>/dev/null || true
    echo -e "${GREEN}done${NC}"
fi

# 3. Remove volumes
if [[ -n "$VOLUMES" ]]; then
    echo -n "  Removing volumes... "
    echo "$VOLUMES" | xargs docker volume rm -f 2>/dev/null || true
    echo -e "${GREEN}done${NC}"
fi

# 4. Remove networks
if [[ -n "$NETWORKS" ]]; then
    echo -n "  Removing networks... "
    echo "$NETWORKS" | xargs docker network rm 2>/dev/null || true
    echo -e "${GREEN}done${NC}"
fi

# 5. Preserve models, remove install dir
if [[ -d "$INSTALL_DIR" ]]; then
    # Backup models (they take forever to download)
    if [[ -d "$INSTALL_DIR/models" ]] && [[ "$(ls -A "$INSTALL_DIR/models" 2>/dev/null)" ]]; then
        echo -n "  Backing up models to /tmp/dream-models-backup... "
        sudo rm -rf /tmp/dream-models-backup 2>/dev/null || true
        mv "$INSTALL_DIR/models" /tmp/dream-models-backup
        echo -e "${GREEN}done${NC}"
    fi
    echo -n "  Removing $INSTALL_DIR... "
    # Use sudo because Docker containers create root-owned files in data dirs
    sudo rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}done${NC}"
fi

# 6. Remove desktop shortcut
if [[ -f "$DESKTOP_FILE" ]]; then
    echo -n "  Removing desktop shortcut... "
    rm -f "$DESKTOP_FILE"
    echo -e "${GREEN}done${NC}"
fi

# 7. Unpin from GNOME
if echo "$FAVORITES" | grep -q "dream-server"; then
    echo -n "  Unpinning from GNOME sidebar... "
    NEW_FAVS=$(echo "$FAVORITES" | sed "s/, 'dream-server.desktop'//g; s/'dream-server.desktop', //g; s/'dream-server.desktop'//g")
    gsettings set org.gnome.shell favorite-apps "$NEW_FAVS" 2>/dev/null || true
    echo -e "${GREEN}done${NC}"
fi

# 8. Prune ALL Docker images and build cache
if $FULL_CLEAN; then
    echo -n "  Removing ALL Docker images and build cache... "
    docker system prune -a --volumes -f &>/dev/null || true
    echo -e "${GREEN}done${NC}"
else
    echo -n "  Pruning dangling images... "
    docker image prune -f 2>/dev/null | tail -1 || true
    echo ""
fi

# ── Full dependency removal ─────────────────────────────────
if $FULL_CLEAN; then
    echo ""
    echo -e "${YELLOW}Removing installer dependencies...${NC}"

    # NVIDIA Container Toolkit
    if $HAS_NVIDIA_CTK; then
        echo -n "  Removing NVIDIA Container Toolkit... "
        sudo apt-get remove -y nvidia-container-toolkit &>/dev/null || true
        sudo apt-get autoremove -y &>/dev/null || true
        # Remove the nvidia-container-toolkit apt repo
        sudo rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list 2>/dev/null || true
        sudo rm -f /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg 2>/dev/null || true
        echo -e "${GREEN}done${NC}"
    fi

    # Docker (includes compose v2 plugin)
    if $HAS_DOCKER; then
        echo -n "  Removing Docker Engine and Compose... "
        sudo apt-get remove -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin &>/dev/null || true
        sudo apt-get autoremove -y &>/dev/null || true
        # Remove Docker apt repo
        sudo rm -f /etc/apt/sources.list.d/docker.list 2>/dev/null || true
        sudo rm -f /etc/apt/keyrings/docker.asc 2>/dev/null || true
        # Remove Docker data (images, containers, volumes already gone)
        sudo rm -rf /var/lib/docker /var/lib/containerd 2>/dev/null || true
        # Remove Docker config
        rm -rf "$HOME/.docker" 2>/dev/null || true
        echo -e "${GREEN}done${NC}"
    fi
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
if $FULL_CLEAN; then
echo -e "${GREEN}║   Full clean complete. Bare metal ready.     ║${NC}"
else
echo -e "${GREEN}║   Clean complete. Ready for fresh install.   ║${NC}"
fi
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"

if [[ -d "/tmp/dream-models-backup" ]]; then
    echo ""
    echo -e "${CYAN}Models backed up to /tmp/dream-models-backup${NC}"
    echo -e "${CYAN}The installer will detect and restore them automatically,${NC}"
    echo -e "${CYAN}or you can manually move them back after install:${NC}"
    echo -e "${CYAN}  mv /tmp/dream-models-backup \$HOME/dream-server/models${NC}"
fi

if $FULL_CLEAN; then
    echo ""
    echo -e "${YELLOW}Dependency status after clean:${NC}"
    command -v docker &>/dev/null  && echo -e "  ${RED}Docker:${NC} still present (may need reboot)" || echo -e "  ${GREEN}Docker:${NC} removed"
    command -v nvidia-ctk &>/dev/null && echo -e "  ${RED}NVIDIA CTK:${NC} still present" || echo -e "  ${GREEN}NVIDIA CTK:${NC} removed"
    echo ""
    echo -e "${CYAN}The installer will re-install all dependencies from scratch.${NC}"
fi
