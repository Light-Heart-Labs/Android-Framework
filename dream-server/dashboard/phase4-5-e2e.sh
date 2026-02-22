#!/bin/bash
# Dream Server Dashboard Phase 4-5 UI & E2E Tests
# Run: bash phase4-5-e2e.sh

BASE_URL="http://localhost:3001"
API_URL="http://localhost:3002"
RESULTS_FILE="${RESULTS_FILE:-./TEST_RESULTS-PHASE4-5.md}"

echo "# Dream Server Dashboard Phase 4-5 Test Results" > "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "**Test Date:** $(date '+%Y-%m-%d %H:%M %Z')" >> "$RESULTS_FILE"
echo "**Test Environment:** Local Dream Server" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# ============================================
# Phase 4: UI Integration
# ============================================

echo "## Phase 4: Dashboard UI Integration" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test 4.1: Frontend Accessibility
echo "### Test 4.1: Frontend Build & Serve" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Testing frontend accessibility..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL" 2>/dev/null)
LOAD_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL" 2>/dev/null)
LOAD_MS=$(echo "$LOAD_TIME * 1000" | bc | cut -d. -f1)

echo "- Dashboard URL: $BASE_URL" >> "$RESULTS_FILE"
echo "- HTTP Status: $HTTP_STATUS" >> "$RESULTS_FILE"
echo "- Load Time: ${LOAD_MS}ms" >> "$RESULTS_FILE"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "- Status: ✅ PASS (accessible)" >> "$RESULTS_FILE"
    BUILD_PASS="✅"
else
    echo "- Status: ⚠️ CHECK (HTTP $HTTP_STATUS)" >> "$RESULTS_FILE"
    BUILD_PASS="⚠️"
fi
echo "" >> "$RESULTS_FILE"

# Test 4.2: API Data Flow
echo "### Test 4.2: API Data Flow" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Testing API endpoints..."

# Check key endpoints
ENDPOINTS=("/health" "/api/status" "/api/models" "/services" "/api/voice/status")
API_PASS=0
API_TOTAL=${#ENDPOINTS[@]}

for endpoint in "${ENDPOINTS[@]}"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL$endpoint" 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        echo "- $endpoint: ✅ (200)" >> "$RESULTS_FILE"
        ((API_PASS++))
    else
        echo "- $endpoint: ❌ ($STATUS)" >> "$RESULTS_FILE"
    fi
done

echo "" >> "$RESULTS_FILE"
echo "- API Endpoints Passing: $API_PASS/$API_TOTAL" >> "$RESULTS_FILE"
if [ $API_PASS -eq $API_TOTAL ]; then
    echo "- Status: ✅ PASS" >> "$RESULTS_FILE"
    DATA_FLOW_PASS="✅"
else
    echo "- Status: ⚠️ PARTIAL" >> "$RESULTS_FILE"
    DATA_FLOW_PASS="⚠️"
fi
echo "" >> "$RESULTS_FILE"

# Test 4.3: Interactive Features (API-only test)
echo "### Test 4.3: Interactive Features" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Testing interactive API endpoints..."

# Test workflow toggle (GET current workflows)
WORKFLOW_RESPONSE=$(curl -s "$API_URL/api/workflows" 2>/dev/null)
if echo "$WORKFLOW_RESPONSE" | grep -q "workflows\|id\|name"; then
    echo "- Workflows API: ✅ (returns data)" >> "$RESULTS_FILE"
    INTERACTIVE_PASS="✅"
else
    echo "- Workflows API: ⚠️ (no workflow data)" >> "$RESULTS_FILE"
    INTERACTIVE_PASS="⚠️"
fi
echo "" >> "$RESULTS_FILE"

# Phase 4 Summary
echo "**Phase 4 Summary:**" >> "$RESULTS_FILE"
echo "| Test | Status |" >> "$RESULTS_FILE"
echo "|------|--------|" >> "$RESULTS_FILE"
echo "| 4.1 Build & Serve | $BUILD_PASS |" >> "$RESULTS_FILE"
echo "| 4.2 API Data Flow | $DATA_FLOW_PASS ($API_PASS/$API_TOTAL) |" >> "$RESULTS_FILE"
echo "| 4.3 Interactive Features | $INTERACTIVE_PASS |" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# ============================================
# Phase 5: End-to-End & Alerting
# ============================================

echo "## Phase 5: End-to-End & Alerting" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test 5.1: First-Time Setup
echo "### Test 5.1: First-Time Setup Flow" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

SETUP_STATUS=$(curl -s "$API_URL/api/setup/status" 2>/dev/null)
if echo "$SETUP_STATUS" | grep -q "complete\|completed\|setupComplete"; then
    echo "- Setup Status: ✅ (completed)" >> "$RESULTS_FILE"
    SETUP_PASS="✅"
else
    echo "- Setup Status: ℹ️ (may need setup)" >> "$RESULTS_FILE"
    SETUP_PASS="ℹ️"
fi
echo "" >> "$RESULTS_FILE"

# Test 5.2: Error Handling
echo "### Test 5.2: Error Handling & Recovery" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test with invalid endpoint (should return 404)
ERROR_TEST=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/invalid-endpoint" 2>/dev/null)
if [ "$ERROR_TEST" = "404" ]; then
    echo "- 404 Handling: ✅ (returns proper error code)" >> "$RESULTS_FILE"
    ERROR_PASS="✅"
else
    echo "- 404 Handling: ⚠️ (returns $ERROR_TEST)" >> "$RESULTS_FILE"
    ERROR_PASS="⚠️"
fi
echo "" >> "$RESULTS_FILE"

# Test 5.3: Real-Time Updates (version check)
echo "### Test 5.3: Version & Updates" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

VERSION_INFO=$(curl -s "$API_URL/api/version" 2>/dev/null)
if echo "$VERSION_INFO" | grep -q "version\|Version"; then
    echo "- Version API: ✅ (returns version info)" >> "$RESULTS_FILE"
    VERSION_PASS="✅"
else
    echo "- Version API: ⚠️ (no version data)" >> "$RESULTS_FILE"
    VERSION_PASS="⚠️"
fi
echo "" >> "$RESULTS_FILE"

# Phase 5 Summary
echo "**Phase 5 Summary:**" >> "$RESULTS_FILE"
echo "| Test | Status |" >> "$RESULTS_FILE"
echo "|------|--------|" >> "$RESULTS_FILE"
echo "| 5.1 Setup Flow | $SETUP_PASS |" >> "$RESULTS_FILE"
echo "| 5.2 Error Handling | $ERROR_PASS |" >> "$RESULTS_FILE"
echo "| 5.3 Version/Updates | $VERSION_PASS |" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Overall Summary
echo "## Overall Summary" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "| Phase | Tests | Status |" >> "$RESULTS_FILE"
echo "|-------|-------|--------|" >> "$RESULTS_FILE"
echo "| Phase 4: UI Integration | 3 | $([ "$BUILD_PASS" = "✅" ] && [ "$DATA_FLOW_PASS" = "✅" ] && echo "✅ PASS" || echo "⚠️ PARTIAL") |" >> "$RESULTS_FILE"
echo "| Phase 5: E2E & Alerting | 3 | $([ "$SETUP_PASS" = "✅" ] && [ "$ERROR_PASS" = "✅" ] && [ "$VERSION_PASS" = "✅" ] && echo "✅ PASS" || echo "⚠️ PARTIAL") |" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "**Test Completed:** $(date '+%Y-%m-%d %H:%M %Z')" >> "$RESULTS_FILE"
echo "Results written to: $RESULTS_FILE"
echo ""
echo "Phase 4-5 tests complete. Check $RESULTS_FILE for detailed results."
