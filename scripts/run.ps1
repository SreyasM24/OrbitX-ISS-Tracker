<#
.SYNOPSIS
  Start the OrbitX dashboard using the project's own virtual environment.
.PARAMETER Port
  Local port (default 8501).
.PARAMETER Offline
  Never use the network: use the cached or bundled sample orbital elements.
.PARAMETER NoBrowser
  Do not open the web browser automatically.
.EXAMPLE
  .\scripts\run.ps1
  .\scripts\run.ps1 -Offline
#>
[CmdletBinding()]
param(
    [int]$Port = 8501,
    [switch]$Offline,
    [switch]$NoBrowser
)

# 'Stop' would turn harmless stderr text from native tools (pip notices) into errors in
# Windows PowerShell 5.1, so native commands are judged by their exit code instead.
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot   # works from any current directory
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: .venv was not found. Run  .\scripts\setup.ps1  first." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $Root 'frontend\app.py'))) {
    Write-Host "ERROR: frontend\app.py not found in $Root." -ForegroundColor Red
    exit 1
}

if ($Offline) {
    $env:ORBITX_OFFLINE = '1'
    Write-Host "Offline mode: no network requests will be made." -ForegroundColor Yellow
}

$Url = "http://localhost:$Port"
Write-Host "Starting OrbitX at $Url  (press Ctrl+C to stop)"

$process = Start-Process -FilePath $VenvPython -WorkingDirectory $Root -NoNewWindow -PassThru `
    -ArgumentList @('-m', 'streamlit', 'run', 'frontend/app.py', '--server.port', "$Port", '--server.headless', 'true')

if (-not $NoBrowser) {
    for ($i = 0; $i -lt 30 -and -not $process.HasExited; $i++) {
        try {
            Invoke-WebRequest "$Url/_stcore/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
            Start-Process $Url
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
}

$process.WaitForExit()
exit $process.ExitCode
