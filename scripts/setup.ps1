<#
.SYNOPSIS
  One-time OrbitX setup for Windows PowerShell 5.1+ (no administrator rights needed).
.DESCRIPTION
  Creates .venv only if it does not exist, installs the dependencies from
  requirements-dev.txt into it, installs OrbitX in editable mode and checks the imports.
  Safe to re-run. Use -Recreate to delete and rebuild .venv.
.EXAMPLE
  .\scripts\setup.ps1
#>
[CmdletBinding()]
param([switch]$Recreate)

# 'Stop' would turn harmless stderr text from native tools (pip notices) into errors in
# Windows PowerShell 5.1, so native commands are judged by their exit code instead.
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Fail([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Test-Python([string]$Exe, [string[]]$ExtraArgs) {
    # True if this interpreter runs and is Python 3.10 or newer.
    try {
        & $Exe @ExtraArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

$VenvDir = Join-Path $Root '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'

if ($Recreate -and (Test-Path $VenvDir)) {
    Write-Host "Removing existing .venv ..."
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $VenvPython)) {
    $bootstrap = $null
    foreach ($candidate in @(@('py', '-3'), @('python'), @('python3'))) {
        $exe = $candidate[0]
        $extra = @($candidate | Select-Object -Skip 1)
        if ((Get-Command $exe -ErrorAction SilentlyContinue) -and (Test-Python $exe $extra)) {
            $bootstrap = @{ Exe = $exe; Args = $extra }
            break
        }
    }
    if (-not $bootstrap) {
        Fail "Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then open a new PowerShell window and re-run this script."
    }
    Write-Host "Creating virtual environment in .venv ..."
    & $bootstrap.Exe @($bootstrap.Args) -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        Fail "Could not create the virtual environment."
    }
} else {
    Write-Host ".venv already exists; keeping it."
}

if (-not (Test-Python $VenvPython @())) {
    Fail ".venv does not contain a working Python 3.10+. Re-run with -Recreate to rebuild it."
}

# "Activate" for this script's process only: later commands resolve to the venv.
$env:VIRTUAL_ENV = $VenvDir
$env:PATH = (Join-Path $VenvDir 'Scripts') + ';' + $env:PATH

Write-Host "Using interpreter:"
& $VenvPython -c "import sys; print('  ' + sys.executable); print('  Python ' + sys.version.split()[0])"

Write-Host "Installing dependencies (needs internet the first time) ..."
& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $Root 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) {
    Fail "Dependency installation failed. Check your internet connection, then re-run this script."
}

& $VenvPython -m pip install --disable-pip-version-check -e $Root --no-deps
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: editable install failed. The app and tests still work, but scripts you write yourself may not find 'orbitx'." -ForegroundColor Yellow
}

& $VenvPython -c "import orbitx, skyfield, streamlit, folium, plotly, pandas, requests; print('Imports OK: orbitx', orbitx.__version__, '| skyfield', skyfield.__version__, '| streamlit', streamlit.__version__)"
if ($LASTEXITCODE -ne 0) {
    Fail "The packages installed but could not be imported."
}

Write-Host ""
Write-Host "Setup complete. Start the app with:  .\scripts\run.ps1" -ForegroundColor Green
Write-Host "To use your own terminal in this environment:  .\.venv\Scripts\Activate.ps1"
