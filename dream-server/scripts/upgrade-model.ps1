# Dream Server Model Upgrade Script (Windows)
# Upgrades from bootstrap model to full tier model
#
# Usage: .\upgrade-model.ps1
#        .\upgrade-model.ps1 -Model "Qwen/Qwen2.5-32B-Instruct-AWQ"

param(
    [string]$Model = "",
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$InstallDir = "$env:LOCALAPPDATA\DreamServer"
$EnvFile = "$InstallDir\.env"

function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Ok { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Warn { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "[ERROR] $args" -ForegroundColor Red }

if ($Help) {
    @"
Dream Server Model Upgrade

Upgrades from bootstrap (small) model to full tier model.

Usage:
    .\upgrade-model.ps1              # Upgrade to target model from .env
    .\upgrade-model.ps1 -Model X     # Upgrade to specific model
    .\upgrade-model.ps1 -DryRun      # Preview without changes

Models by tier:
    Tier 1: Qwen/Qwen2.5-7B-Instruct
    Tier 2: Qwen/Qwen2.5-14B-Instruct-AWQ
    Tier 3: Qwen/Qwen2.5-32B-Instruct-AWQ
    Tier 4: Qwen/Qwen2.5-72B-Instruct-AWQ
"@
    exit 0
}

# Check installation exists
if (-not (Test-Path $InstallDir)) {
    Write-Err "Dream Server not installed at $InstallDir"
    Write-Info "Run install-windows.bat first"
    exit 1
}

if (-not (Test-Path $EnvFile)) {
    Write-Err ".env file not found"
    exit 1
}

# Read current config
$envContent = Get-Content $EnvFile -Raw
$currentModel = ""
$targetModel = ""

if ($envContent -match 'LLM_MODEL=(.+)') {
    $currentModel = $Matches[1].Trim()
}
if ($envContent -match 'TARGET_MODEL=(.+)') {
    $targetModel = $Matches[1].Trim()
}

Write-Host ""
Write-Host "Dream Server Model Upgrade" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
Write-Host ""
Write-Info "Current model: $currentModel"

# Determine target
if ($Model) {
    $newModel = $Model
} elseif ($targetModel -and $targetModel -ne $currentModel) {
    $newModel = $targetModel
} else {
    Write-Warn "No target model specified and TARGET_MODEL matches current"
    Write-Info "Use -Model to specify a model manually"
    exit 0
}

Write-Info "Target model:  $newModel"

if ($currentModel -eq $newModel) {
    Write-Ok "Already running target model. No upgrade needed."
    exit 0
}

if ($DryRun) {
    Write-Host ""
    Write-Info "[DRY RUN] Would update LLM_MODEL from '$currentModel' to '$newModel'"
    Write-Info "[DRY RUN] Would restart vLLM container"
    exit 0
}

Write-Host ""
Write-Info "Upgrading model..."

# Update .env file
$envContent = $envContent -replace "LLM_MODEL=.+", "LLM_MODEL=$newModel"
$envContent | Set-Content $EnvFile -NoNewline
Write-Ok "Updated .env"

# Restart vLLM to load new model
Set-Location $InstallDir
Write-Info "Restarting vLLM container (this will download the model)..."
Write-Warn "This may take 10-30 minutes depending on model size and internet speed"

docker compose stop vllm
docker compose up -d vllm

Write-Host ""
Write-Info "Model download starting in background."
Write-Info "Monitor progress with: docker compose logs -f vllm"
Write-Host ""

# Wait a bit and check status
Write-Info "Waiting 30s for initial startup..."
Start-Sleep -Seconds 30

$health = docker compose exec vllm curl -s http://localhost:8000/health 2>&1
if ($health -match "200" -or $health -match "ok") {
    Write-Ok "vLLM is responding (model may still be loading)"
} else {
    Write-Warn "vLLM not responding yet - check logs"
}

Write-Host ""
Write-Ok "Upgrade initiated!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Monitor: docker compose logs -f vllm"
Write-Host "  2. Wait for 'Running on http://0.0.0.0:8000' in logs"
Write-Host "  3. Test: curl http://localhost:8000/health"
Write-Host ""
