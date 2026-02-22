# Dream Server Preflight Check for Windows
# Usage: .\scripts\dream-preflight.ps1

param(
    [switch]$Fix
)

$ErrorActionPreference = "Continue"
$global:Issues = @()
$global:Warnings = @()

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
}

function Test-Prereq {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$FixCmd = "",
        [string]$DocsLink = ""
    )
    
    Write-Host "Checking $Name... " -NoNewline
    try {
        $result = & $Test
        if ($result) {
            Write-Host "OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "FAIL" -ForegroundColor Red
            $global:Issues += @{
                Name = $Name
                Fix = $FixCmd
                Docs = $DocsLink
            }
            return $false
        }
    } catch {
        Write-Host "FAIL" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor DarkGray
        $global:Issues += @{
            Name = $Name
            Fix = $FixCmd
            Docs = $DocsLink
        }
        return $false
    }
}

function Test-Warning {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$Advice = ""
    )
    
    Write-Host "Checking $Name... " -NoNewline
    try {
        $result = & $Test
        if ($result) {
            Write-Host "OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "WARN" -ForegroundColor Yellow
            if ($Advice) {
                Write-Host "  $Advice" -ForegroundColor DarkYellow
            }
            $global:Warnings += @{
                Name = $Name
                Advice = $Advice
            }
            return $false
        }
    } catch {
        Write-Host "WARN" -ForegroundColor Yellow
        Write-Host "  $Advice" -ForegroundColor DarkYellow
        $global:Warnings += @{
            Name = $Name
            Advice = $Advice
        }
        return $false
    }
}

Write-Header "Dream Server Preflight Check (Windows)"

# Windows version
Test-Prereq "Windows Version" {
    $winVer = [System.Environment]::OSVersion.Version
    return $winVer.Build -ge 19041
} -FixCmd "Update to Windows 10 version 2004+ or Windows 11" -DocsLink "https://aka.ms/windows-update"

# WSL2 installed
$wslInstalled = Test-Prereq "WSL2 Installation" {
    $status = wsl --status 2>&1
    return $LASTEXITCODE -eq 0
} -FixCmd "wsl --install" -DocsLink "https://docs.microsoft.com/en-us/windows/wsl/install"

# WSL2 default version
if ($wslInstalled) {
    Test-Prereq "WSL2 Default Version" {
        $status = wsl --status 2>&1 | Out-String
        return $status -match "Default Version: 2"
    } -FixCmd "wsl --set-default-version 2" -DocsLink "docs/WINDOWS-WSL2-GPU-GUIDE.md"
}

# Ubuntu distro
Test-Prereq "Ubuntu WSL Distro" {
    $distros = wsl -l -q 2>&1
    return $distros -match "Ubuntu"
} -FixCmd "wsl --install -d Ubuntu" -DocsLink "docs/WINDOWS-WSL2-GPU-GUIDE.md"

# Docker Desktop installed
$dockerInstalled = Test-Prereq "Docker Desktop" {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    return $null -ne $docker
} -FixCmd "Install from https://docker.com/products/docker-desktop" -DocsLink "docs/WINDOWS-WSL2-GPU-GUIDE.md"

# Docker running
if ($dockerInstalled) {
    Test-Prereq "Docker Running" {
        $info = docker info 2>&1
        return $LASTEXITCODE -eq 0
    } -FixCmd "Start Docker Desktop from Start Menu" -DocsLink "docs/WINDOWS-WSL2-GPU-GUIDE.md"
}

# WSL2 backend
Test-Warning "Docker WSL2 Backend" {
    $info = docker info 2>&1 | Out-String
    return $info -match "WSL"
} -Advice "Enable WSL2 backend in Docker Desktop settings for GPU support"

# NVIDIA drivers on Windows
$nvidiaWindows = Test-Prereq "NVIDIA Drivers (Windows)" {
    $smi = nvidia-smi 2>&1
    return $LASTEXITCODE -eq 0
} -FixCmd "Install from https://www.nvidia.com/drivers" -DocsLink "docs/WINDOWS-WSL2-GPU-GUIDE.md"

# GPU in WSL2
if ($nvidiaWindows) {
    Test-Prereq "GPU in WSL2" {
        $wslSmi = wsl nvidia-smi 2>&1
        return $LASTEXITCODE -eq 0
    } -FixCmd "See WSL2 GPU troubleshooting" -DocsLink "docs/WINDOWS-WSL2-GPU-GUIDE.md"
    
    # GPU memory check
    try {
        $gpuMem = wsl nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>&1 | Select-Object -First 1
        $gpuMemNum = [int]$gpuMem.Trim()
        if ($gpuMemNum -lt 8192) {
            Write-Host "  GPU VRAM: ${gpuMemNum}MB" -ForegroundColor Yellow
            Write-Host "  Warning: 8GB+ VRAM recommended for Dream Server" -ForegroundColor DarkYellow
        } else {
            Write-Host "  GPU VRAM: ${gpuMemNum}MB" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Could not detect GPU memory" -ForegroundColor DarkGray
    }
}

# GPU in Docker (most critical)
if ($nvidiaWindows -and $dockerInstalled) {
    Test-Prereq "GPU in Docker" {
        $result = docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi 2>&1
        return $LASTEXITCODE -eq 0
    } -FixCmd "Enable WSL2 integration in Docker Desktop settings" -DocsLink "docs/WINDOWS-WSL2-GPU-GUIDE.md"
}

# Memory check
$totalMem = (Get-CimInstance -ClassName Win32_ComputerSystem).TotalPhysicalMemory / 1GB
$wslMem = ""
try {
    $wslConfig = Get-Content "$env:USERPROFILE\.wslconfig" -ErrorAction SilentlyContinue
    $wslMemMatch = $wslConfig | Select-String "memory=(\d+)"
    if ($wslMemMatch) {
        $wslMem = $wslMemMatch.Matches[0].Groups[1].Value
    }
} catch {}

Write-Host ""
Write-Host "System Memory: $([math]::Round($totalMem, 1)) GB total" -ForegroundColor Cyan
if ($wslMem) {
    Write-Host "WSL2 Memory: $wslMem GB (from .wslconfig)" -ForegroundColor Cyan
} else {
    Write-Host "WSL2 Memory: $([math]::Round($totalMem * 0.5, 1)) GB (default 50%)" -ForegroundColor Yellow
    Write-Host "  Consider creating .wslconfig to increase memory" -ForegroundColor DarkYellow
}

if ($totalMem -lt 16) {
    Write-Host "  Warning: 16GB+ RAM recommended" -ForegroundColor Yellow
}

# Summary
Write-Header "Summary"

if ($global:Issues.Count -eq 0 -and $global:Warnings.Count -eq 0) {
    Write-Host "All checks passed! Ready to install Dream Server." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run: .\install.ps1"
    Write-Host "  2. After install: cd ~/dream-server && ./scripts/dream-preflight.sh"
} else {
    if ($global:Issues.Count -gt 0) {
        Write-Host "BLOCKERS ($($global:Issues.Count)):" -ForegroundColor Red
        foreach ($issue in $global:Issues) {
            Write-Host "  - $($issue.Name)" -ForegroundColor Red
            if ($issue.Fix) {
                Write-Host "    Fix: $($issue.Fix)" -ForegroundColor DarkGray
            }
            if ($issue.Docs) {
                Write-Host "    See: $($issue.Docs)" -ForegroundColor DarkGray
            }
        }
    }
    
    if ($global:Warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "WARNINGS ($($global:Warnings.Count)):" -ForegroundColor Yellow
        foreach ($warn in $global:Warnings) {
            Write-Host "  - $($warn.Name)" -ForegroundColor Yellow
            if ($warn.Advice) {
                Write-Host "    $($warn.Advice)" -ForegroundColor DarkGray
            }
        }
    }
    
    Write-Host ""
    Write-Host "Fix the blockers above, then run this script again." -ForegroundColor Cyan
}

Write-Host ""
