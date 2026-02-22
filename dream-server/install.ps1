# Dream Server Installer for Windows (WSL2 + Docker Desktop)
# Version 2.1.0
#
# Run via batch file to bypass execution policy:
#   install-windows.bat [OPTIONS]
#
# Or directly if policy allows:
#   .\install.ps1 [OPTIONS]

param(
    [switch]$DryRun,
    [switch]$Force,
    [int]$Tier = 0,
    [switch]$Voice,
    [switch]$Workflows,
    [switch]$Rag,
    [switch]$All,
    [switch]$Bootstrap,
    [switch]$NoBootstrap,
    [switch]$Diagnose,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$Version = "2.1.0"
$InstallDir = "$env:LOCALAPPDATA\DreamServer"  # Avoids spaces in path

# Colors
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Ok { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Warn { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "[ERROR] $args" -ForegroundColor Red }

function Show-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Blue
    Write-Host "  $Title" -ForegroundColor Blue
    Write-Host ("=" * 60) -ForegroundColor Blue
}

function Show-Help {
    @"
Dream Server Installer for Windows v$Version

Usage: install-windows.bat [OPTIONS]
       .\install.ps1 [OPTIONS]

Options:
    -DryRun         Show what would be done without making changes
    -Force          Overwrite existing installation
    -Tier N         Force specific tier (1-4) instead of auto-detect
    -Voice          Enable voice services (Whisper + TTS)
    -Workflows      Enable n8n workflow automation
    -Rag            Enable RAG with Qdrant vector database
    -All            Enable all optional services
    -Bootstrap      Start with small model, upgrade later (faster first start)
    -NoBootstrap    Skip bootstrap, download full model immediately
    -Diagnose       Run diagnostics only (don't install)
    -Help           Show this help

Prerequisites:
    - Windows 10 version 2004+ or Windows 11
    - WSL2 enabled
    - Docker Desktop with WSL2 backend
    - NVIDIA GPU with latest drivers (for GPU acceleration)

Tiers:
    1 - Entry Level   (8GB+ VRAM, 7B models)
    2 - Prosumer      (12GB+ VRAM, 14B-32B AWQ models)  
    3 - Pro           (24GB+ VRAM, 32B models)
    4 - Enterprise    (48GB+ VRAM or dual GPU, 72B models)

Examples:
    install-windows.bat                    # Interactive setup
    install-windows.bat -Tier 2 -Voice     # Tier 2 with voice
    install-windows.bat -All               # Full stack
    install-windows.bat -Bootstrap         # Quick start with small model
    install-windows.bat -Diagnose          # Check system only
    install-windows.bat -DryRun            # Preview installation

Troubleshooting:
    See docs/WSL2-GPU-TROUBLESHOOTING.md for common issues.
"@
    exit 0
}

if ($Help) { Show-Help }
if ($All) { $Voice = $true; $Workflows = $true; $Rag = $true }

# Diagnose mode - just run checks and exit
if ($Diagnose) {
    Write-Host ""
    Write-Host "Dream Server System Diagnostics" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    # Fall through to prerequisites, will exit after hardware detection
}

#=============================================================================
# Prerequisites Check
#=============================================================================
Show-Header "Checking Prerequisites"

# Check PowerShell execution policy (show warning only)
$execPolicy = Get-ExecutionPolicy
if ($execPolicy -eq "Restricted" -or $execPolicy -eq "AllSigned") {
    Write-Warn "PowerShell execution policy is '$execPolicy'"
    Write-Info "If this script fails to run, use: powershell -ExecutionPolicy Bypass -File install.ps1"
    Write-Info "Or run via: install-windows.bat (handles this automatically)"
}

# Windows Defender / antivirus warning
Write-Info "Tip: If install fails with GPU access errors, Windows Defender may be blocking Docker."
Write-Info "     See docs/WINDOWS-WSL2-GPU-GUIDE.md for antivirus exclusion steps."
Write-Host ""

# Check Windows version
$winVer = [System.Environment]::OSVersion.Version
if ($winVer.Build -lt 19041) {
    Write-Err "Windows 10 version 2004 (build 19041) or later required"
    Write-Err "Current build: $($winVer.Build)"
    exit 1
}
Write-Ok "Windows version: $($winVer.Major).$($winVer.Minor) build $($winVer.Build)"

# Check WSL2
$wslStatus = wsl --status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "WSL2 is not installed or not configured"
    Write-Info "Run: wsl --install"
    exit 1
}
Write-Ok "WSL2 is available"

# Check for Ubuntu distro
$distros = wsl -l -q 2>&1
if (-not ($distros -match "Ubuntu")) {
    Write-Warn "Ubuntu WSL distro not found"
    Write-Info "Installing Ubuntu..."
    if (-not $DryRun) {
        wsl --install -d Ubuntu
        Write-Info "Ubuntu installed. Please restart and run this script again."
        exit 0
    }
}
Write-Ok "Ubuntu WSL distro available"

# Check Docker Desktop
$dockerPath = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerPath) {
    Write-Err "Docker Desktop not found"
    Write-Info "Please install Docker Desktop from: https://docker.com/products/docker-desktop"
    exit 1
}

# Check Docker is running
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker Desktop is not running"
    Write-Info "Please start Docker Desktop and try again"
    exit 1
}
Write-Ok "Docker Desktop is running"

# Check WSL2 backend
if (-not ($dockerInfo -match "WSL")) {
    Write-Warn "Docker may not be using WSL2 backend"
    Write-Info "Recommended: Enable WSL2 backend in Docker Desktop settings"
}

# Check NVIDIA Container Toolkit
Write-Info "Testing GPU access in Docker (this may take a moment on first run)..."
try {
    $nvidiaDocker = docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "NVIDIA Container Toolkit working"
        $GpuInDocker = $true
    } else {
        Write-Warn "NVIDIA GPU support not detected in Docker"
        Write-Info "See docs/WSL2-GPU-TROUBLESHOOTING.md for help"
        $GpuInDocker = $false
    }
} catch {
    Write-Warn "Could not test GPU access: $_"
    Write-Info "See docs/WSL2-GPU-TROUBLESHOOTING.md for help"
    $GpuInDocker = $false
}

#=============================================================================
# Hardware Detection
#=============================================================================
Show-Header "Detecting Hardware"

# Run PowerShell detection script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$detectScript = Join-Path $scriptDir "scripts\detect-hardware.ps1"

if (Test-Path $detectScript) {
    $hwInfo = & $detectScript -Json | ConvertFrom-Json
    $GpuVram = $hwInfo.gpu.vram_gb
    $GpuName = $hwInfo.gpu.name
    $RamGb = $hwInfo.ram_gb
    $CpuCores = $hwInfo.cores
    
    Write-Ok "CPU: $($hwInfo.cpu)"
    Write-Ok "RAM: ${RamGb}GB"
    if ($GpuName) {
        Write-Ok "GPU: $GpuName (${GpuVram}GB VRAM)"
    } else {
        Write-Warn "No GPU detected"
    }
} else {
    # Fallback detection
    try {
        $nvidiaSmi = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>$null
        if ($nvidiaSmi) {
            $parts = $nvidiaSmi -split ','
            $GpuName = $parts[0].Trim()
            $GpuVram = [math]::Floor([int]$parts[1].Trim() / 1024)
            Write-Ok "GPU: $GpuName (${GpuVram}GB VRAM)"
        }
    } catch {
        $GpuVram = 0
        Write-Warn "No NVIDIA GPU detected"
    }
    
    $RamGb = [math]::Floor((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
    Write-Ok "RAM: ${RamGb}GB"
}

# Auto-detect tier
if ($Tier -eq 0) {
    if ($GpuVram -ge 48) { $Tier = 4 }
    elseif ($GpuVram -ge 20) { $Tier = 3 }
    elseif ($GpuVram -ge 12) { $Tier = 2 }
    else { $Tier = 1 }
    Write-Info "Auto-detected tier: $Tier"
} else {
    Write-Info "Using specified tier: $Tier"
}

$tierNames = @{
    1 = "Entry Level (7B models)"
    2 = "Prosumer (14B-32B AWQ models)"
    3 = "Pro (32B models)"
    4 = "Enterprise (72B models)"
}
Write-Ok "Selected: Tier $Tier - $($tierNames[$Tier])"

# Diagnose mode exits here
if ($Diagnose) {
    Write-Host ""
    Write-Host "Diagnostics complete." -ForegroundColor Green
    Write-Host ""
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  Windows:     OK"
    Write-Host "  WSL2:        OK"
    Write-Host "  Docker:      OK"
    Write-Host "  GPU Docker:  $(if ($GpuInDocker) { 'OK' } else { 'WARN - see troubleshooting guide' })"
    Write-Host "  GPU VRAM:    ${GpuVram}GB"
    Write-Host "  Tier:        $Tier - $($tierNames[$Tier])"
    Write-Host ""
    exit 0
}

#=============================================================================
# Installation
#=============================================================================
Show-Header "Installing Dream Server"

if ($DryRun) {
    Write-Info "[DRY RUN] Would create: $InstallDir"
    Write-Info "[DRY RUN] Would copy Docker configs"
    Write-Info "[DRY RUN] Would set tier: $Tier"
    Write-Info "[DRY RUN] Voice: $Voice, Workflows: $Workflows, RAG: $Rag"
    exit 0
}

# Create install directory
if (Test-Path $InstallDir) {
    if ($Force) {
        Write-Warn "Removing existing installation..."
        Remove-Item -Recurse -Force $InstallDir
    } else {
        Write-Err "Installation directory exists: $InstallDir"
        Write-Info "Use -Force to overwrite"
        exit 1
    }
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Write-Ok "Created: $InstallDir"

# Copy files
Copy-Item "$scriptDir\docker-compose.yml" "$InstallDir\"
Copy-Item "$scriptDir\.env.example" "$InstallDir\.env"
Copy-Item -Recurse "$scriptDir\scripts" "$InstallDir\"
Copy-Item -Recurse "$scriptDir\configs" "$InstallDir\" -ErrorAction SilentlyContinue
Write-Ok "Copied configuration files"

# Configure .env
$envFile = "$InstallDir\.env"
$envContent = Get-Content $envFile

# Set tier-specific model
$models = @{
    1 = "Qwen/Qwen2.5-7B-Instruct"
    2 = "Qwen/Qwen2.5-14B-Instruct-AWQ"
    3 = "Qwen/Qwen2.5-32B-Instruct-AWQ"
    4 = "Qwen/Qwen2.5-72B-Instruct-AWQ"
}
$bootstrapModel = "Qwen/Qwen2.5-1.5B-Instruct"

# Determine model to use
if ($Bootstrap -and -not $NoBootstrap) {
    $selectedModel = $bootstrapModel
    $targetModel = $models[$Tier]
    Write-Info "Bootstrap mode: Starting with small model for quick setup"
    Write-Info "  Initial: $bootstrapModel"
    Write-Info "  Target:  $targetModel (upgrade later with 'dream upgrade-model')"
} else {
    $selectedModel = $models[$Tier]
    $targetModel = $selectedModel
}

$envContent = $envContent -replace 'LLM_MODEL=.*', "LLM_MODEL=$selectedModel"
$envContent = $envContent -replace 'TARGET_MODEL=.*', "TARGET_MODEL=$targetModel"
$envContent | Set-Content $envFile
Write-Ok "Configured model: $selectedModel"

#=============================================================================
# Build Profiles
#=============================================================================
$profiles = @("core")
if ($Voice) { $profiles += "voice" }
if ($Workflows) { $profiles += "workflows" }
if ($Rag) { $profiles += "rag" }

$profileStr = $profiles -join ","
Write-Info "Profiles: $profileStr"

# Start services
Show-Header "Starting Services"
Set-Location $InstallDir

Write-Info "Pulling Docker images (this may take a while)..."
docker compose --profile $profileStr pull

Write-Info "Starting containers..."
docker compose --profile $profileStr up -d

# Wait for services
Write-Info "Waiting for services to be ready..."
Start-Sleep -Seconds 30

#=============================================================================
# Verify Installation
#=============================================================================
Show-Header "Verifying Installation"

$services = @{
    "vLLM" = "http://localhost:8000/health"
    "Open WebUI" = "http://localhost:3000"
}
if ($Voice) {
    $services["Whisper"] = "http://localhost:9000/health"
}
if ($Rag) {
    $services["Qdrant"] = "http://localhost:6333/health"
}

foreach ($svc in $services.Keys) {
    try {
        $response = Invoke-WebRequest -Uri $services[$svc] -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Ok "$svc is running"
        }
    } catch {
        Write-Warn "$svc not responding yet (may still be starting)"
    }
}

#=============================================================================
# Done
#=============================================================================
Show-Header "Installation Complete!"

Write-Host ""
Write-Host "Your Dream Server is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Access points:"
Write-Host "  - Chat UI:  http://localhost:3000"
Write-Host "  - API:      http://localhost:8000/v1"
if ($Voice) {
    Write-Host "  - Whisper:  http://localhost:9000"
}
if ($Workflows) {
    Write-Host "  - n8n:      http://localhost:5678"
}
if ($Rag) {
    Write-Host "  - Qdrant:   http://localhost:6333"
}
Write-Host ""
Write-Host "Manage your server:"
Write-Host "  cd $InstallDir"
Write-Host "  docker compose logs -f        # View logs"
Write-Host "  docker compose down           # Stop"
Write-Host "  docker compose up -d          # Start"

if ($Bootstrap -and -not $NoBootstrap) {
    Write-Host ""
    Write-Host "Bootstrap Mode Active" -ForegroundColor Yellow
    Write-Host "  You're running a small model for quick setup."
    Write-Host "  Upgrade to full model when ready:"
    Write-Host "    .\scripts\upgrade-model.ps1"
    Write-Host "  Target model: $targetModel"
}

Write-Host ""
Write-Host "Troubleshooting: docs\WSL2-GPU-TROUBLESHOOTING.md"
Write-Host ""
Write-Host "Your AI, your hardware, your data. Welcome to Dream Server." -ForegroundColor Cyan
