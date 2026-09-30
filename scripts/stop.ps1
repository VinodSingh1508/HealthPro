# Stops the HealthPro backend and frontend.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$stopped = Stop-HealthPro
$remaining = Get-PortOwners -Ports @($HealthProBackendPort, $HealthProFrontendPort)

if ($remaining) {
    Write-Output "Could not free ports; still held by PID(s): $($remaining -join ', ')"
    exit 1
}

Write-Output "HealthPro stopped ($stopped process(es))."
exit 0
