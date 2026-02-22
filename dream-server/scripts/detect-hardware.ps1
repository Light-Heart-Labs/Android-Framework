# Dream Server Hardware Detection (Windows)
# Detects GPU, CPU, RAM and recommends tier

param(
    [switch]$Json
)

function Get-GpuInfo {
    $gpu = @{
        type = "none"
        name = ""
        vram_mb = 0
        vram_gb = 0
    }
    
    # Try nvidia-smi first
    try {
        $nvidiaSmi = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>$null
        if ($nvidiaSmi) {
            $parts = $nvidiaSmi -split ','
            $gpu.type = "nvidia"
            $gpu.name = $parts[0].Trim()
            $gpu.vram_mb = [int]$parts[1].Trim()
            $gpu.vram_gb = [math]::Floor($gpu.vram_mb / 1024)
            return $gpu
        }
    } catch {}
    
    # Fallback to WMI
    try {
        $wmiGpu = Get-WmiObject Win32_VideoController | Where-Object { $_.AdapterRAM -gt 0 } | Select-Object -First 1
        if ($wmiGpu) {
            $gpu.type = "generic"
            $gpu.name = $wmiGpu.Name
            $gpu.vram_mb = [math]::Floor($wmiGpu.AdapterRAM / 1024 / 1024)
            $gpu.vram_gb = [math]::Floor($gpu.vram_mb / 1024)
            return $gpu
        }
    } catch {}
    
    return $gpu
}

function Get-CpuInfo {
    try {
        $cpu = Get-WmiObject Win32_Processor | Select-Object -First 1
        return @{
            name = $cpu.Name
            cores = $cpu.NumberOfCores
            threads = $cpu.NumberOfLogicalProcessors
        }
    } catch {
        return @{
            name = "Unknown"
            cores = 0
            threads = 0
        }
    }
}

function Get-RamGb {
    try {
        $ram = Get-WmiObject Win32_ComputerSystem
        return [math]::Floor($ram.TotalPhysicalMemory / 1024 / 1024 / 1024)
    } catch {
        return 0
    }
}

function Get-Tier {
    param([int]$VramGb)
    
    if ($VramGb -ge 48) { return "T4" }
    elseif ($VramGb -ge 20) { return "T3" }
    elseif ($VramGb -ge 12) { return "T2" }
    else { return "T1" }
}

function Get-TierDescription {
    param([string]$Tier)
    
    switch ($Tier) {
        "T4" { return "Ultimate (48GB+): Full 70B models, multi-model serving" }
        "T3" { return "Pro (20-47GB): 32B models, comfortable headroom" }
        "T2" { return "Starter (12-19GB): 7-14B models, lean configs" }
        "T1" { return "Mini (<12GB): Small models or CPU inference" }
    }
}

# Main
$gpu = Get-GpuInfo
$cpu = Get-CpuInfo
$ram = Get-RamGb
$tier = Get-Tier -VramGb $gpu.vram_gb
$tierDesc = Get-TierDescription -Tier $tier

if ($Json) {
    @{
        os = "windows"
        cpu = $cpu.name
        cores = $cpu.cores
        ram_gb = $ram
        gpu = $gpu
        tier = $tier
        tier_description = $tierDesc
    } | ConvertTo-Json
} else {
    Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║      Dream Server Hardware Detection     ║" -ForegroundColor Blue
    Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
    Write-Host "System:" -ForegroundColor Green
    Write-Host "  OS:       Windows"
    Write-Host "  CPU:      $($cpu.name)"
    Write-Host "  Cores:    $($cpu.cores)"
    Write-Host "  RAM:      ${ram}GB"
    Write-Host ""
    Write-Host "GPU:" -ForegroundColor Green
    if ($gpu.name) {
        Write-Host "  Type:     $($gpu.type)"
        Write-Host "  Name:     $($gpu.name)"
        Write-Host "  VRAM:     $($gpu.vram_gb)GB"
    } else {
        Write-Host "  No GPU detected (CPU-only mode)"
    }
    Write-Host ""
    Write-Host "Recommended Tier: $tier" -ForegroundColor Yellow
    Write-Host "  $tierDesc"
    Write-Host ""
}
