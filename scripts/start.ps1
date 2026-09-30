# Starts the HealthPro backend and frontend with hidden windows.
# Double-click scripts\start.cmd, or run: .\scripts\start.ps1
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$python = Join-Path $HealthProRoot ".venv\Scripts\python.exe"
$viteEntry = Join-Path $HealthProRoot "frontend\node_modules\vite\bin\vite.js"

if (-not (Test-Path $python)) {
    Write-Output "Missing venv. Run: python -m venv .venv ; .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt"
    exit 1
}
if (-not (Test-Path $viteEntry)) {
    Write-Output "Missing frontend deps. Run: cd frontend ; npm install"
    exit 1
}
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Output "node was not found on PATH. Install Node.js."
    exit 1
}

New-Item -ItemType Directory -Force -Path $HealthProLogDir | Out-Null
Stop-HealthPro | Out-Null

$backendOut = Join-Path $HealthProLogDir "backend.out.log"
$backendErr = Join-Path $HealthProLogDir "backend.err.log"
$frontendOut = Join-Path $HealthProLogDir "frontend.out.log"
$frontendErr = Join-Path $HealthProLogDir "frontend.err.log"

$backend = Start-Process -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$HealthProBackendPort") `
    -WorkingDirectory (Join-Path $HealthProRoot "backend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -PassThru

$frontend = Start-Process -FilePath $node.Source `
    -ArgumentList @($viteEntry, "--host", "127.0.0.1", "--port", "$HealthProFrontendPort", "--strictPort") `
    -WorkingDirectory (Join-Path $HealthProRoot "frontend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -PassThru

@($backend.Id, $frontend.Id) | Set-Content -Path $HealthProPidFile -Encoding ascii

$backendUp = Wait-ForHttp -Url "http://127.0.0.1:$HealthProBackendPort/api/health"
$frontendUp = Wait-ForHttp -Url "http://127.0.0.1:$HealthProFrontendPort/"

if ($backendUp -and $frontendUp) {
    Write-Output "HealthPro is running."
    Write-Output "  UI:   http://127.0.0.1:$HealthProFrontendPort"
    Write-Output "  API:  http://127.0.0.1:$HealthProBackendPort"
    Write-Output "  Stop: double-click scripts\stop.cmd"
    exit 0
}

if (-not $backendUp) {
    Write-Output "Backend did not start. Last lines of backend.err.log:"
    Get-Content $backendErr -Tail 15 -ErrorAction SilentlyContinue
}
if (-not $frontendUp) {
    Write-Output "Frontend did not start. Last lines of frontend.err.log:"
    Get-Content $frontendErr -Tail 15 -ErrorAction SilentlyContinue
}
exit 1
