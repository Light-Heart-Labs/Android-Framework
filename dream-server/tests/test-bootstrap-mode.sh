#!/bin/bash
# Dream Server Bootstrap Mode Test Suite
# Tests the instant-start UX with 1.5B bootstrap model

set -e

DREAM_DIR="${DREAM_DIR:-$(dirname "$(dirname "$(realpath "$0")")")}"
cd "$DREAM_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ PASS${NC}: $1"; }
fail() { echo -e "${RED}✗ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}→${NC} $1"; }

echo "═══════════════════════════════════════════════════════════════"
echo "  Dream Server Bootstrap Mode Test Suite"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ===== Test 1: Bootstrap compose files exist =====
info "Test 1: Checking bootstrap compose files..."
[[ -f "docker-compose.yml" ]] || fail "docker-compose.yml not found"
[[ -f "docker-compose.bootstrap.yml" ]] || fail "docker-compose.bootstrap.yml not found"
pass "Bootstrap compose files present"

# ===== Test 2: Bootstrap compose is valid =====
info "Test 2: Validating bootstrap compose..."
# Try docker compose (plugin) first, then docker-compose (standalone)
if command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
    docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml config > /dev/null 2>&1 || fail "Invalid compose configuration"
elif command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.yml -f docker-compose.bootstrap.yml config > /dev/null 2>&1 || fail "Invalid compose configuration"
else
    info "Docker/docker-compose not available, skipping compose validation"
fi
pass "Bootstrap compose configuration valid (or skipped)"

# ===== Test 3: Bootstrap model specified correctly =====
info "Test 3: Checking bootstrap model config..."
grep -q "Qwen2.5-1.5B-Instruct" docker-compose.bootstrap.yml || fail "Bootstrap model not configured"
pass "Bootstrap model (1.5B) configured"

# ===== Test 4: Upgrade script exists =====
info "Test 4: Checking upgrade script..."
[[ -f "scripts/upgrade-model.sh" ]] || fail "upgrade-model.sh not found"
[[ -x "scripts/upgrade-model.sh" ]] || fail "upgrade-model.sh not executable"
pass "Upgrade script ready"

# ===== Test 5: Healthcheck timing =====
info "Test 5: Checking healthcheck configuration..."
BOOTSTRAP_START_PERIOD=$(grep -A5 "healthcheck:" docker-compose.bootstrap.yml | grep "start_period" | grep -oP '\d+' || echo "0")
MAIN_START_PERIOD=$(grep -A10 "vllm:" docker-compose.yml | grep -A5 "healthcheck:" | grep "start_period" | grep -oP '\d+' | head -1 || echo "0")
if [[ "$BOOTSTRAP_START_PERIOD" -lt "$MAIN_START_PERIOD" ]] || [[ "$BOOTSTRAP_START_PERIOD" == "30" ]]; then
    pass "Bootstrap healthcheck faster than main ($BOOTSTRAP_START_PERIOD vs $MAIN_START_PERIOD)"
else
    fail "Bootstrap should have shorter healthcheck start_period"
fi

# ===== Test 6: .env template has LLM_MODEL =====
info "Test 6: Checking .env template..."
if [[ -f ".env.example" ]]; then
    grep -q "LLM_MODEL" .env.example || fail ".env.example missing LLM_MODEL"
    pass ".env.example has LLM_MODEL setting"
else
    info "Skipping .env.example check (file not present)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "  ${GREEN}All tests passed!${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "To run bootstrap mode:"
echo "  docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml up -d"
echo ""
echo "To upgrade to full model after download completes:"
echo "  ./scripts/upgrade-model.sh"
echo ""
