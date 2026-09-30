# Shared helpers for start/stop scripts.

$HealthProRoot = Split-Path -Parent $PSScriptRoot
$HealthProLogDir = Join-Path $HealthProRoot "logs"
$HealthProPidFile = Join-Path $HealthProLogDir "healthpro.pids"
$HealthProBackendPort = 8000
$HealthProFrontendPort = 5173

function Get-PortOwners {
    param([int[]]$Ports)

    $owners = @()
    foreach ($port in $Ports) {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $conns) {
            $owners += [int]$conn.OwningProcess
        }
    }
    return $owners | Select-Object -Unique
}

function Get-DescendantPids {
    param([int]$ParentId)

    $found = @()
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        $found += [int]$child.ProcessId
        $found += Get-DescendantPids -ParentId ([int]$child.ProcessId)
    }
    return $found
}

function Stop-HealthPro {
    $targets = @()

    if (Test-Path $HealthProPidFile) {
        foreach ($line in Get-Content $HealthProPidFile) {
            $trimmed = $line.Trim()
            if ($trimmed -match '^\d+$') {
                $targets += [int]$trimmed
                $targets += Get-DescendantPids -ParentId ([int]$trimmed)
            }
        }
    }

    $targets += Get-PortOwners -Ports @($HealthProBackendPort, $HealthProFrontendPort)
    $targets = $targets | Select-Object -Unique

    $stopped = 0
    foreach ($procId in $targets) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            $stopped++
        }
    }

    if (Test-Path $HealthProPidFile) {
        Remove-Item $HealthProPidFile -Force -ErrorAction SilentlyContinue
    }

    # Ports can linger for a moment after the owning process exits.
    for ($i = 0; $i -lt 10; $i++) {
        if (-not (Get-PortOwners -Ports @($HealthProBackendPort, $HealthProFrontendPort))) { break }
        Start-Sleep -Milliseconds 300
    }

    return $stopped
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 40
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
            return $true
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}
