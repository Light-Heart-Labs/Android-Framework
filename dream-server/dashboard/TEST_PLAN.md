# Dream Server Dashboard Test Plan

**Project:** Dream Server Dashboard (React SPA + FastAPI Backend)  
**Location:** `dream-server/dashboard/` (frontend) + `dream-server/dashboard-api/` (backend)  
**Version:** 1.0.0  
**Date:** 2026-02-12

---

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [API Endpoint Tests](#api-endpoint-tests)
4. [UI Component Tests](#ui-component-tests)
5. [Integration Tests](#integration-tests)
6. [Performance Tests](#performance-tests)
7. [Test Execution Checklist](#test-execution-checklist)

---

## Overview

### Architecture

- **Frontend:** React SPA with Vite, React Router, Tailwind CSS
- **Backend:** FastAPI (Python) on port 3002
- **Frontend Port:** 3001 (dev) / served via nginx (production)

### Key API Groups

1. **Health & Status** - System health, GPU metrics, service status
2. **Models** - Model catalog, download, load, delete
3. **Voice** - LiveKit tokens, STT/TTS health
4. **Workflows** - n8n integration, workflow enable/disable
5. **Features** - Feature discovery, recommendations
6. **Setup** - First-run wizard, diagnostics
7. **Privacy** - Privacy Shield status/toggle
8. **Version/Updates** - Version checking, update triggers

---

## Test Environment Setup

### Prerequisites

```bash
# Start the full stack
cd dream-server
docker compose up -d

# Or start just the dashboard + API
cd dashboard-api
pip install -r requirements.txt
python main.py

cd dashboard
npm install
npm run dev
```

### Environment Variables

```bash
export DREAM_INSTALL_DIR=~/dream-server
export DREAM_DATA_DIR=~/.dream-server
export SERVICE_HOST=host.docker.internal
export VLLM_URL=http://localhost:8000
export N8N_URL=http://localhost:5678
export WHISPER_URL=http://localhost:9000
export KOKORO_URL=http://localhost:8880
export LIVEKIT_URL=ws://localhost:7880
export LIVEKIT_API_KEY=<from-your-.env>
export LIVEKIT_API_SECRET=<from-your-.env>
```

---

## API Endpoint Tests

### 1. Health Endpoints

#### 1.1 GET /health
```bash
curl -s http://localhost:3002/health | jq
```
**Expected:** `{"status": "ok", "timestamp": "..."}`  
**Status Code:** 200

#### 1.2 GET /api/status (Dashboard Format)
```bash
curl -s http://localhost:3002/api/status | jq
```
**Expected Fields:**
- `gpu`: name, vramUsed, vramTotal, utilization, temperature
- `services`: array of {name, status, port, uptime}
- `model`: name, tokensPerSecond, contextLength
- `bootstrap`: active, model, percent, bytesDownloaded, bytesTotal, eta, speedMbps
- `uptime`: number (seconds)
- `version`: string
- `tier`: string (Entry/Prosumer/Pro/Enterprise)

---

### 2. GPU & System Metrics

#### 2.1 GET /gpu (Raw Format)
```bash
curl -s http://localhost:3002/gpu | jq
```
**Expected:** GPUInfo model with memory_used_mb, memory_total_mb, etc.

#### 2.2 GET /services
```bash
curl -s http://localhost:3002/services | jq
```
**Expected:** Array of ServiceStatus objects

#### 2.3 GET /disk
```bash
curl -s http://localhost:3002/disk | jq
```
**Expected:** DiskUsage with used_gb, total_gb, percent

#### 2.4 GET /bootstrap
```bash
curl -s http://localhost:3002/bootstrap | jq
```
**Expected:** BootstrapStatus (active: false when no download)

---

### 3. Model Management

#### 3.1 GET /api/models (Catalog)
```bash
curl -s http://localhost:3002/api/models | jq
```
**Expected Fields:**
- `models`: array with id, name, size, vramRequired, status, fitsVram
- `gpu`: vramTotal, vramUsed, vramFree
- `currentModel`: string or null

#### 3.2 POST /api/models/{model_id}/download
```bash
curl -X POST http://localhost:3002/api/models/Qwen%2FQwen2.5-7B-Instruct/download | jq
```
**Expected:** `{"status": "started", "model": "...", "message": "..."}`  
**Status Code:** 200 (or 409 if already downloading)

#### 3.3 GET /api/models/download-status
```bash
curl -s http://localhost:3002/api/models/download-status | jq
```
**Expected:** status (idle/downloading/complete/error), percent, bytesDownloaded, etc.

#### 3.4 POST /api/models/{model_id}/load
```bash
curl -X POST http://localhost:3002/api/models/Qwen%2FQwen2.5-7B-Instruct/load | jq
```
**Expected:** `{"status": "started", "model": "...", "message": "..."}`

#### 3.5 DELETE /api/models/{model_id}
```bash
curl -X DELETE http://localhost:3002/api/models/Qwen%2FQwen2.5-7B-Instruct | jq
```
**Expected:** `{"status": "deleted", "model": "..."}`  
**Status Code:** 200 (or 400 if model loaded, 404 if not found)

---

### 4. Voice API

#### 4.1 POST /api/voice/token
```bash
curl -X POST http://localhost:3002/api/voice/token \
  -H "Content-Type: application/json" \
  -d '{"identity": "test-user", "room": "test-room"}' | jq
```
**Expected:** `{"token": "...", "room": "...", "livekitUrl": "..."}`  
**Status Code:** 200 (or 500 if LiveKit SDK not available)

#### 4.2 GET /api/voice/status
```bash
curl -s http://localhost:3002/api/voice/status | jq
```
**Expected Fields:**
- `available`: boolean
- `services`: {stt, tts, livekit} with status
- `message`: string

#### 4.3 POST /api/voice/transcribe (with file)
```bash
curl -X POST http://localhost:3002/api/voice/transcribe \
  -F "audio=@test-audio.webm" | jq
```
**Expected:** `{"text": "...", "success": true}`  
**Status Code:** 200 (or 503 if Whisper unavailable)

---

### 5. Workflow API

#### 5.1 GET /api/workflows
```bash
curl -s http://localhost:3002/api/workflows | jq
```
**Expected Fields:**
- `workflows`: array with id, name, status, dependencies, allDependenciesMet
- `categories`: object
- `n8nUrl`: string
- `n8nAvailable`: boolean

#### 5.2 POST /api/workflows/{workflow_id}/enable
```bash
curl -X POST http://localhost:3002/api/workflows/document-qa/enable | jq
```
**Expected:** `{"status": "success", "workflowId": "...", "n8nId": "...", "activated": true}`  
**Status Code:** 200 (or 400 if dependencies missing, 503 if n8n unreachable)

#### 5.3 DELETE /api/workflows/{workflow_id}
```bash
curl -X DELETE http://localhost:3002/api/workflows/document-qa | jq
```
**Expected:** `{"status": "success", "message": "..."}`

#### 5.4 GET /api/workflows/{workflow_id}/executions
```bash
curl -s http://localhost:3002/api/workflows/document-qa/executions?limit=10 | jq
```
**Expected:** `{"executions": [...], "workflowId": "..."}`

---

### 6. Feature Discovery API

#### 6.1 GET /api/features
```bash
curl -s http://localhost:3002/api/features | jq
```
**Expected Fields:**
- `features`: array with id, name, status, enabled, requirements
- `summary`: enabled, available, total, progress
- `suggestions`: top 3 suggestions
- `recommendations`: tier-based recommendations
- `gpu`: name, vramGb, tier

#### 6.2 GET /api/features/{feature_id}/enable
```bash
curl -s http://localhost:3002/api/features/voice/enable | jq
```
**Expected:** `{"featureId": "...", "name": "...", "instructions": {...}}`

---

### 7. Setup Wizard API

#### 7.1 GET /api/setup/status
```bash
curl -s http://localhost:3002/api/setup/status | jq
```
**Expected:** `{"first_run": boolean, "step": number, "persona": string|null, "personas_available": [...]}`

#### 7.2 POST /api/setup/persona
```bash
curl -X POST http://localhost:3002/api/setup/persona \
  -H "Content-Type: application/json" \
  -d '{"persona": "coding"}' | jq
```
**Expected:** `{"success": true, "persona": "...", "name": "...", "message": "..."}`

#### 7.3 POST /api/setup/complete
```bash
curl -X POST http://localhost:3002/api/setup/complete | jq
```
**Expected:** `{"success": true, "redirect": "/", "message": "..."}`

#### 7.4 GET /api/setup/personas
```bash
curl -s http://localhost:3002/api/setup/personas | jq
```
**Expected:** `{"personas": [{"id": "...", "name": "...", "system_prompt": "...", "icon": "..."}]}`

#### 7.5 POST /api/setup/test (Streaming)
```bash
curl -N http://localhost:3002/api/setup/test
```
**Expected:** Streaming text output of diagnostic tests

---

### 8. Chat API

#### 8.1 POST /api/chat
```bash
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "system": "You are helpful."}' | jq
```
**Expected:** `{"response": "...", "success": true}`  
**Status Code:** 200 (or 503 if vLLM unavailable)

---

### 9. Version & Update API

#### 9.1 GET /api/version
```bash
curl -s http://localhost:3002/api/version | jq
```
**Expected Fields:**
- `current`: string
- `latest`: string|null
- `update_available`: boolean
- `changelog_url`: string|null
- `checked_at`: string

#### 9.2 GET /api/releases/manifest
```bash
curl -s http://localhost:3002/api/releases/manifest | jq
```
**Expected:** `{"releases": [...], "checked_at": "..."}`

#### 9.3 POST /api/update
```bash
# Check
curl -X POST http://localhost:3002/api/update \
  -H "Content-Type: application/json" \
  -d '{"action": "check"}' | jq

# Backup
curl -X POST http://localhost:3002/api/update \
  -H "Content-Type: application/json" \
  -d '{"action": "backup"}' | jq

# Update
curl -X POST http://localhost:3002/api/update \
  -H "Content-Type: application/json" \
  -d '{"action": "update"}' | jq
```
**Expected:** Varies by action (check returns update_available, backup returns success/output, update returns "started")

---

### 10. Privacy Shield API

#### 10.1 GET /api/privacy-shield/status
```bash
curl -s http://localhost:3002/api/privacy-shield/status | jq
```
**Expected:** `{"enabled": boolean, "container_running": boolean, "port": number, "target_api": "...", "pii_cache_enabled": boolean, "message": "..."}`

#### 10.2 POST /api/privacy-shield/toggle
```bash
curl -X POST http://localhost:3002/api/privacy-shield/toggle \
  -H "Content-Type: application/json" \
  -d '{"enable": true}' | jq
```
**Expected:** `{"success": boolean, "message": "..."}`

#### 10.3 GET /api/privacy-shield/stats
```bash
curl -s http://localhost:3002/api/privacy-shield/stats | jq
```
**Expected:** Stats object or `{"error": "...", "enabled": false}`

---

### 11. Preflight Check API

#### 11.1 GET /api/preflight/docker
```bash
curl -s http://localhost:3002/api/preflight/docker | jq
```
**Expected:** `{"available": boolean, "version": "..."}`

#### 11.2 GET /api/preflight/gpu
```bash
curl -s http://localhost:3002/api/preflight/gpu | jq
```
**Expected:** `{"available": boolean, "name": "...", "vram": number}`

#### 11.3 POST /api/preflight/ports
```bash
curl -X POST http://localhost:3002/api/preflight/ports \
  -H "Content-Type: application/json" \
  -d '{"ports": [3000, 3001, 8000]}' | jq
```
**Expected:** `{"conflicts": [...]}`

#### 11.4 GET /api/preflight/disk
```bash
curl -s http://localhost:3002/api/preflight/disk | jq
```
**Expected:** `{"free": number, "total": number}`

---

### 12. Agent Monitoring API

#### 12.1 GET /api/agents/metrics
```bash
curl -s http://localhost:3002/api/agents/metrics | jq
```
**Expected:** Full metrics including agent, cluster, tokens, throughput

#### 12.2 GET /api/agents/metrics.html
```bash
curl -s http://localhost:3002/api/agents/metrics.html
```
**Expected:** HTML fragment for htmx

#### 12.3 GET /api/agents/cluster
```bash
curl -s http://localhost:3002/api/agents/cluster | jq
```
**Expected:** Cluster status with active_gpus, total_gpus, failover_ready

#### 12.4 GET /api/agents/tokens
```bash
curl -s http://localhost:3002/api/agents/tokens | jq
```
**Expected:** Token usage stats (24h)

#### 12.5 GET /api/agents/throughput
```bash
curl -s http://localhost:3002/api/agents/throughput | jq
```
**Expected:** Throughput metrics (tokens/sec)

---

## UI Component Tests

### 1. SetupWizard Component

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| SW-001 | First run detection | Component renders when `dream-dashboard-visited` not in localStorage |
| SW-002 | Step navigation | Click Next/Back moves between steps (1-5) |
| SW-003 | Step 1: PreFlight | PreFlightChecks component renders, Docker/GPU/Port/Disk checks run |
| SW-004 | Step 2: Welcome | Welcome text displays, user can proceed to step 3 |
| SW-005 | Step 3: Name input | Input accepts name, Next disabled if empty |
| SW-006 | Step 4: Voice selection | All 5 voices display (af_heart, af_bella, af_sky, am_adam, am_michael) |
| SW-007 | Step 5: Diagnostics | Click Start Diagnostics calls `/api/setup/test`, streams output |
| SW-008 | Complete setup | Saves config to localStorage, calls onComplete callback |
| SW-009 | Progress indicator | Shows correct step (X of 5), completed steps show checkmark |

**Test Commands:**
```bash
# Clear localStorage to trigger first run
localStorage.removeItem('dream-dashboard-visited')
localStorage.removeItem('dream-config')
```

---

### 2. PreFlightChecks Component

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| PFC-001 | Auto-run checks | Runs all checks on mount |
| PFC-002 | Docker check | Calls `/api/preflight/docker`, shows version or error |
| PFC-003 | GPU check | Calls `/api/preflight/gpu`, shows GPU name + VRAM |
| PFC-004 | Port check | Calls `/api/preflight/ports`, lists conflicts if any |
| PFC-005 | Disk check | Calls `/api/preflight/disk`, shows free space |
| PFC-006 | Error display | Shows fix suggestion for errors |
| PFC-007 | Retry button | Re-runs all checks when clicked |
| PFC-008 | onComplete callback | Called when all checks pass |
| PFC-009 | onIssuesFound callback | Called when issues found |

---

### 3. Sidebar Component

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| SB-001 | Navigation items | Shows Dashboard, Models, Voice, Workflows, Settings |
| SB-002 | Active state | Highlights current route |
| SB-003 | External links | Shows Chat (WebUI) link with external icon |
| SB-004 | Service status footer | Shows healthy/total count, green/yellow indicator |
| SB-005 | VRAM display | Shows VRAM bar if GPU data available |
| SB-006 | Version display | Shows tier and version in header |

---

### 4. Dashboard Page

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| DB-001 | Feature cards | Shows 6 cards (Chat, Voice, Documents, Workflows, Agents, System) |
| DB-002 | Card status | Ready/disabled/coming badges correct |
| DB-003 | System metrics | Shows GPU, VRAM, Temperature, Speed cards |
| DB-004 | Services grid | Shows all services with status dots |
| DB-005 | Feature discovery | Shows FeatureDiscoveryBanner if suggestions available |
| DB-006 | Bootstrap banner | Shows progress if bootstrap.active |
| DB-007 | Loading state | Shows skeleton loaders while fetching |

---

### 5. Models Page

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| MD-001 | Model list | Fetches and displays models from `/api/models` |
| MD-002 | VRAM indicator | Shows VRAM usage bar |
| MD-003 | Download progress | Shows progress bar if downloading |
| MD-004 | Model card states | Shows Download/Load/Active buttons based on status |
| MD-005 | Download action | Calls POST `/api/models/{id}/download` |
| MD-006 | Load action | Calls POST `/api/models/{id}/load`, disabled if !fitsVram |
| MD-007 | Delete action | Calls DELETE `/api/models/{id}`, confirms before delete |
| MD-008 | Refresh button | Re-fetches model list |

---

### 6. Voice Page

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| VP-001 | Services banner | Fetches `/api/voice/status`, shows healthy/unhealthy |
| VP-002 | Connect button | Calls hook connect, status changes to "connecting" then "connected" |
| VP-003 | Mic toggle | Click toggles isListening state |
| VP-004 | Transcription | Displays messages from useVoiceAgent |
| VP-005 | Interim text | Shows currentTranscript while speaking |
| VP-006 | AI speaking | Shows waveform animation when isSpeaking |
| VP-007 | Volume control | Slider adjusts volume, mute button works |
| VP-008 | Interrupt button | Sends interrupt signal when clicked |
| VP-009 | Settings modal | Opens voice settings when gear clicked |
| VP-010 | Keyboard shortcut | Spacebar toggles listening |

---

### 7. Workflows Page

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| WF-001 | Workflow list | Fetches `/api/workflows`, displays cards |
| WF-002 | Featured section | Shows featured workflows first |
| WF-003 | Category grouping | Groups workflows by category |
| WF-004 | n8n status banner | Shows warning if n8n unavailable |
| WF-005 | Enable workflow | Calls POST `/api/workflows/{id}/enable` |
| WF-006 | Disable workflow | Calls DELETE `/api/workflows/{id}` with confirmation |
| WF-007 | Dependency check | Shows missing dependencies, disables enable button |
| WF-008 | Modal open | Shows workflow details in modal |

---

### 8. Settings Page

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| ST-001 | System info | Shows version, install date, tier, uptime |
| ST-002 | Storage display | Shows Models, Vector DB, Docker usage bars |
| ST-003 | Update check | Button triggers update check |
| ST-004 | Action buttons | Export, Restart, Uninstall buttons visible |

---

### 9. FeatureDiscovery Components

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| FD-001 | Banner display | Shows top suggestion from `/api/features` |
| FD-002 | Progress card | Shows enabled/total progress bar |
| FD-003 | Feature grid | Shows all features with status badges |
| FD-004 | Feature click | Opens enable instructions modal |
| FD-005 | Dismiss banner | Click X dismisses banner |

---

### 10. TroubleshootingAssistant Component

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| TA-001 | Issue list | Shows all common issues |
| TA-002 | Search filter | Filters issues by title/symptoms |
| TA-003 | Relevant detection | Auto-detects issues from unhealthy services |
| TA-004 | Expand issue | Click shows symptoms, cause, solutions |
| TA-005 | Copy command | Copy button copies command to clipboard |

---

### 11. SuccessValidation Component

| Test Case | Steps | Expected Result |
|-----------|-------|-----------------|
| SV-001 | Test display | Shows LLM, Voice, Documents, Workflows tests |
| SV-002 | Status icons | Shows check/running/fail icons correctly |
| SV-003 | Run tests | Calls test endpoints, updates status |
| SV-004 | Progress bar | Shows passed/total progress |
| SV-005 | All passed | Shows success banner when all pass |

---

### 12. Custom Hooks

| Test Case | Hook | Expected Behavior |
|-----------|------|-------------------|
| HK-001 | useSystemStatus | Polls `/api/status` every 5s, returns status/loading/error |
| HK-002 | useModels | Polls `/api/models` every 30s, provides download/load/delete actions |
| HK-003 | useDownloadProgress | Polls `/api/models/download-status` every 1s during download |
| HK-004 | useVersion | Checks `/api/version` every 30min, provides dismissUpdate |
| HK-005 | useVoiceAgent | Manages LiveKit connection, provides connect/toggleListening/interrupt |

---

## Integration Tests

### 1. First-Run Workflow

```bash
# Test the complete first-run experience
curl -X POST http://localhost:3002/api/setup/complete  # Mark as complete first to reset
rm ~/.dream-server/config/setup-complete.json  # Remove to trigger first run
```

| Step | Action | Expected |
|------|--------|----------|
| 1 | Clear localStorage | SetupWizard appears |
| 2 | PreFlight checks | All checks run and display results |
| 3 | Click through wizard | Steps 1-5 navigable |
| 4 | Run diagnostics | Streaming output displays |
| 5 | Complete setup | Config saved, wizard closes |
| 6 | Refresh page | Wizard does not reappear |

---

### 2. Model Download → Load Workflow

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Models | List loads |
| 2 | Click Download | Download starts, progress appears |
| 3 | Wait for complete | Status changes to "downloaded" |
| 4 | Click Load | Model loads, vLLM restarts |
| 5 | Verify chat | Open WebUI responds with new model |

---

### 3. Voice Connection Workflow

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Voice | Services status banner shows |
| 2 | Click mic | Gets token from `/api/voice/token` |
| 3 | Connect to LiveKit | Status changes to "connected" |
| 4 | Speak | Transcript appears |
| 5 | Receive response | AI response displayed, audio plays |
| 6 | Interrupt | Interrupt signal sent |

---

### 4. Workflow Enable → Execute

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Workflows | List loads from n8n |
| 2 | Click Enable on workflow | POST to enable, workflow imports |
| 3 | Verify in n8n | Workflow appears active in n8n |
| 4 | Trigger workflow | Execution recorded |
| 5 | Check executions | GET executions returns data |

---

### 5. Update Workflow

| Step | Action | Expected |
|------|--------|----------|
| 1 | Version check | GET `/api/version` returns current/latest |
| 2 | Trigger check | POST update check runs script |
| 3 | Create backup | POST backup creates backup |
| 4 | Start update | POST update starts background process |
| 5 | Banner dismiss | Dismiss hides update banner |

---

## Performance Tests

### 1. API Response Times

| Endpoint | Target | Max Acceptable |
|----------|--------|----------------|
| GET /health | < 50ms | 200ms |
| GET /api/status | < 500ms | 2000ms |
| GET /api/models | < 200ms | 1000ms |
| GET /api/workflows | < 500ms | 2000ms |
| GET /api/features | < 300ms | 1000ms |
| POST /api/voice/token | < 500ms | 2000ms |
| POST /api/chat | < 2000ms | 10000ms |

**Test Command:**
```bash
# Run with timing
time curl -s http://localhost:3002/api/status > /dev/null

# Apache Bench for load testing
ab -n 100 -c 10 http://localhost:3002/health
```

---

### 2. Frontend Load Performance

| Metric | Target | Max Acceptable |
|--------|--------|----------------|
| First Contentful Paint | < 1.5s | 3s |
| Time to Interactive | < 3s | 5s |
| Bundle size | < 500KB | 1MB |

**Test Command:**
```bash
# Build and analyze
cd dashboard
npm run build
npx vite-bundle-visualizer

# Lighthouse
npx lighthouse http://localhost:3001 --output=json
```

---

### 3. Polling Frequency Tests

| Hook | Interval | Expected Impact |
|------|----------|-----------------|
| useSystemStatus | 5s | Minimal, lightweight endpoint |
| useModels | 30s | OK, but disable during download |
| useDownloadProgress | 1s | Acceptable during active download |
| useVersion | 30min | Negligible |

---

### 4. Concurrent Load Test

```bash
# Simulate 50 concurrent dashboard users
ab -n 1000 -c 50 http://localhost:3002/api/status

# Monitor backend resources
docker stats dream-dashboard-api
```

**Expected:**
- No errors
- Response time degradation < 50%
- Memory usage stable

---

## Test Execution Checklist

### Pre-Test Setup

- [ ] Docker Compose stack running (vLLM, n8n, Qdrant, Whisper, Kokoro, LiveKit)
- [ ] Dashboard API running on port 3002
- [ ] Dashboard frontend running on port 3001
- [ ] Test data cleared (setup-complete.json removed for first-run tests)
- [ ] Browser DevTools open (Network tab)

### API Tests

- [ ] All health endpoints return 200
- [ ] All status endpoints return valid JSON schema
- [ ] Model CRUD operations work
- [ ] Voice token generation works
- [ ] Workflow enable/disable works
- [ ] Feature discovery returns recommendations
- [ ] Setup wizard endpoints work
- [ ] Version check connects to GitHub

### UI Tests

- [ ] SetupWizard flows correctly
- [ ] All navigation items work
- [ ] Models page loads and interacts
- [ ] Voice page connects and streams
- [ ] Workflows page manages n8n
- [ ] Settings display system info
- [ ] Feature discovery suggests features

### Integration Tests

- [ ] First-run complete workflow
- [ ] Model download → load → chat
- [ ] Voice connect → transcribe → respond
- [ ] Workflow enable → execute

### Performance Tests

- [ ] API response times under thresholds
- [ ] Frontend loads within targets
- [ ] Concurrent load handled

### Post-Test Cleanup

- [ ] Test models deleted
- [ ] Test workflows disabled
- [ ] localStorage cleared
- [ ] Test downloads cancelled

---

## Appendix A: Test Data

### Sample Model IDs

```
Qwen/Qwen2.5-1.5B-Instruct
Qwen/Qwen2.5-7B-Instruct
Qwen/Qwen2.5-32B-Instruct-AWQ
Qwen/Qwen2.5-32B-Instruct-AWQ
```

### Sample Workflow IDs

```
document-qa
email-digest
voice-notes
```

### Sample Personas

```
general
coding
creative
```

---

## Appendix B: Automated Testing Commands

```bash
#!/bin/bash
# run-api-tests.sh

BASE_URL="http://localhost:3002"

echo "=== API Health Tests ==="
curl -sf $BASE_URL/health && echo "✓ /health" || echo "✗ /health"

echo "=== Status Endpoints ==="
curl -sf $BASE_URL/api/status > /dev/null && echo "✓ /api/status" || echo "✗ /api/status"
curl -sf $BASE_URL/gpu > /dev/null && echo "✓ /gpu" || echo "✗ /gpu"

echo "=== Model Endpoints ==="
curl -sf $BASE_URL/api/models > /dev/null && echo "✓ /api/models" || echo "✗ /api/models"

echo "=== Voice Endpoints ==="
curl -sf $BASE_URL/api/voice/status > /dev/null && echo "✓ /api/voice/status" || echo "✗ /api/voice/status"

echo "=== Workflow Endpoints ==="
curl -sf $BASE_URL/api/workflows > /dev/null && echo "✓ /api/workflows" || echo "✗ /api/workflows"

echo "=== Feature Endpoints ==="
curl -sf $BASE_URL/api/features > /dev/null && echo "✓ /api/features" || echo "✗ /api/features"

echo "=== Setup Endpoints ==="
curl -sf $BASE_URL/api/setup/status > /dev/null && echo "✓ /api/setup/status" || echo "✗ /api/setup/status"

echo "=== Version Endpoints ==="
curl -sf $BASE_URL/api/version > /dev/null && echo "✓ /api/version" || echo "✗ /api/version"

echo "=== Done ==="
```

---

## Appendix C: Browser Testing Matrix

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | Latest | Required |
| Firefox | Latest | Required |
| Safari | Latest | Recommended |
| Edge | Latest | Recommended |
| Mobile Chrome | Latest | Recommended |
| Mobile Safari | Latest | Recommended |

---

## Phase 3: Benchmark Suite 🔄 IN PROGRESS

**Goal:** Measure performance characteristics and detect regressions  
**Environment:** Local Dream Server with NVIDIA GPU  
**Duration:** ~30 minutes per full run

---

### Test 3.1: Latency Benchmarks
**Objective:** Establish baseline TTFT and tokens/sec metrics

**Test Steps:**
1. Send 20 sequential requests with varying token counts
2. Measure time-to-first-token (TTFT) for each
3. Measure tokens generated per second
4. Calculate p50, p95, p99 latencies

**Test Prompts:**
- Short: "Say hello" (expected ~20 tokens)
- Medium: "Explain quantum computing in simple terms" (expected ~150 tokens)
- Long: "Write a comprehensive guide to local AI deployment" (expected ~500 tokens)

**Expected Results:**
- TTFT < 500ms for all prompt sizes
- Tokens/sec > 50 for GPU inference
- Consistent latency across sequential requests

**Validation Criteria:**
- [ ] All 20 requests complete successfully
- [ ] p95 TTFT < 1 second
- [ ] No timeout errors
- [ ] Tokens/sec within expected range for GPU tier

---

### Test 3.2: Concurrent User Simulation
**Objective:** Test system behavior under 10, 25, 50 concurrent users

**Test Steps:**
1. Simulate 10 concurrent requests (5 iterations)
2. Simulate 25 concurrent requests (5 iterations)
3. Simulate 50 concurrent requests (3 iterations)
4. Measure success rate, latency, and resource usage

**Simulation Pattern:**
```
User 1-10:  Send request → Wait for response → Record metrics
Repeat 5 times with staggered start (0-100ms jitter)
```

**Expected Results:**
- 10 users: 100% success, <2x latency increase
- 25 users: >95% success, <3x latency increase
- 50 users: >90% success, graceful degradation

**Validation Criteria:**
- [ ] 10-user test: 50/50 success
- [ ] 25-user test: >118/125 success
- [ ] 50-user test: >135/150 success
- [ ] No crashes or OOM errors

---

### Test 3.3: Memory Leak Detection
**Objective:** Detect memory leaks over long-running sessions

**Test Steps:**
1. Record baseline memory usage
2. Run 100 sequential conversations
3. Run 100 tool-calling interactions
4. Record memory usage every 25 interactions
5. Compare final memory to baseline

**Monitoring:**
- GPU VRAM usage via nvidia-smi
- Container memory via docker stats
- API response times (slowdown = possible leak)

**Expected Results:**
- Memory returns to near-baseline after GC
- No steady upward trend in memory usage
- Response times remain consistent

**Validation Criteria:**
- [ ] Memory increase < 10% from baseline
- [ ] No OOM kills during test
- [ ] Response time variance < 20%

---

### Test 3.4: Results Comparison Over Time
**Objective:** Track performance changes across releases

**Test Steps:**
1. Save benchmark results with timestamp
2. Compare to previous run (if exists)
3. Flag regressions > 20%
4. Document improvements

**Storage:**
- `benchmark-results/YYYY-MM-DD-results.json`
- Track: TTFT p95, tokens/sec, success rates

**Validation Criteria:**
- [ ] Results saved to versioned file
- [ ] Comparison report generated
- [ ] Regressions flagged for investigation

---

## Phase 4: Dashboard UI Integration 🔄 IN PROGRESS

**Goal:** Verify frontend-backend integration works correctly  
**Environment:** Local Dream Server with dashboard running  
**Duration:** ~15 minutes

---

### Test 4.1: Frontend Build & Serve
**Objective:** Verify React app builds and serves correctly

**Test Steps:**
1. Build frontend: `npm run build`
2. Verify build output exists in `dist/`
3. Serve via nginx or dev server
4. Load dashboard in browser

**Expected Results:**
- Build completes without errors
- All assets generated (JS, CSS, HTML)
- Dashboard loads at http://localhost:3001
- No console errors on load

**Validation Criteria:**
- [ ] Build exits with code 0
- [ ] dist/ folder contains index.html and assets
- [ ] Dashboard accessible in browser
- [ ] Initial load < 3 seconds

---

### Test 4.2: API Data Flow
**Objective:** Verify frontend correctly fetches and displays API data

**Test Steps:**
1. Load dashboard homepage
2. Verify status indicators populate
3. Navigate to Models page
4. Verify model list loads
5. Navigate to Voice page
6. Verify service health displays

**Expected Results:**
- All status indicators show data
- No "Loading..." spinners stuck
- Error states handled gracefully
- Data matches API responses

**Validation Criteria:**
- [ ] Homepage shows system status
- [ ] Models page lists available models
- [ ] Voice page shows STT/TTS status
- [ ] All API calls return 200
- [ ] Errors show user-friendly messages

---

### Test 4.3: Interactive Features
**Objective:** Test user interactions work end-to-end

**Test Steps:**
1. Click "Load Model" button
2. Verify model loading state updates
3. Test workflow enable/disable toggle
4. Verify Privacy Shield toggle works
5. Test dark/light mode switch

**Expected Results:**
- Buttons trigger API calls
- UI updates reflect action results
- Toggle states persist (or sync with backend)
- No JavaScript errors on interaction

**Validation Criteria:**
- [ ] Model load action triggers API call
- [ ] Workflow toggle updates backend state
- [ ] Privacy toggle reflects actual status
- [ ] Theme switch applies immediately

---

## Phase 5: End-to-End & Alerting 🔄 IN PROGRESS

**Goal:** Validate complete user workflows and alerting system  
**Environment:** Full Dream Server stack  
**Duration:** ~20 minutes

---

### Test 5.1: First-Time Setup Flow
**Objective:** Test new user onboarding experience

**Test Steps:**
1. Clear localStorage / cookies
2. Load dashboard
3. Verify setup wizard appears
4. Complete setup steps
5. Verify dashboard appears after completion

**Expected Results:**
- Setup wizard shows on first visit
- Steps guide through basic configuration
- Completion saves state
- Dashboard accessible after setup

**Validation Criteria:**
- [ ] Wizard appears for new users
- [ ] All setup steps completable
- [ ] State persists across reloads
- [ ] Can re-enter wizard from settings

---

### Test 5.2: Error Handling & Recovery
**Objective:** Verify graceful degradation when services fail

**Test Steps:**
1. Stop vLLM container
2. Verify dashboard shows error state
3. Restart vLLM
4. Verify dashboard recovers
5. Test network disconnection handling

**Expected Results:**
- Clear error messages when services down
- Retry logic attempts recovery
- Manual refresh option available
- No crash or freeze on error

**Validation Criteria:**
- [ ] Error state visible when service down
- [ ] Recovery detected after restart
- [ ] Manual retry button works
- [ ] No JavaScript exceptions

---

### Test 5.3: Real-Time Updates
**Objective:** Test WebSocket or polling for live updates

**Test Steps:**
1. Open dashboard in two browser tabs
2. Trigger model load in Tab 1
3. Verify Tab 2 shows loading state
4. Complete download in Tab 1
5. Verify Tab 2 reflects completion

**Expected Results:**
- State changes sync across tabs
- No manual refresh required
- Updates arrive within 5 seconds
- Consistent state across views

**Validation Criteria:**
- [ ] Tab 2 reflects Tab 1 actions
- [ ] Updates arrive < 5 seconds
- [ ] No state desynchronization
- [ ] Both tabs show same data

---

**End of Test Plan**
