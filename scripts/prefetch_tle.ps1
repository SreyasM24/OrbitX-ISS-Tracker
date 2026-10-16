<#
.SYNOPSIS
  Pre-fetch the ISS TLE from CelesTrak before the workshop.
.DESCRIPTION
  Downloads fresh orbital elements, verifies them, prints the epoch and age,
  and writes them to the local cache so all students start with CACHED data.
  Run this ~30 minutes before the session while you have reliable internet.
.EXAMPLE
  .\scripts\prefetch_tle.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot

# ---- resolve Python: prefer .venv, then system ----
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Python = if (Test-Path $VenvPython) { $VenvPython } else { 'python' }

Write-Host ""
Write-Host "OrbitX TLE Pre-fetch" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan
Write-Host "Using Python: $Python"
Write-Host ""

$Script = @"
import sys
sys.path.insert(0, r'$Root')
from backend import tle_service, config
from backend.validation import utcnow

now = utcnow()
print('Fetching from:', config.CELESTRAK_URL)
try:
    data = tle_service.get_orbital_data(force_refresh=True, now=now)
except Exception as exc:
    print(f'ERROR: {exc}', file=sys.stderr)
    sys.exit(1)

age = tle_service.tle_age_days(data.tle, now)
freshness = tle_service.classify_freshness(data.tle, now)

print()
print(f'  Name    : {data.tle.name}')
print(f'  Epoch   : {data.tle.epoch_utc.strftime("%Y-%m-%d %H:%M UTC")}')
print(f'  Age     : {age:.2f} days ({freshness.value.upper()})')
print(f'  Source  : {data.source_label}')
print(f'  Message : {data.status_message}')
if data.warnings:
    for w in data.warnings:
        print(f'  WARNING : {w}')
print()
if freshness.value == 'expired':
    print('CAUTION: Elements are expired. Check your internet connection.', file=sys.stderr)
    sys.exit(2)
print('OK — cache is ready. Students will start with CACHED data.')
"@

& $Python -c $Script
$Exit = $LASTEXITCODE

if ($Exit -eq 0) {
    Write-Host ""
    Write-Host "Pre-fetch complete." -ForegroundColor Green
} elseif ($Exit -eq 2) {
    Write-Host ""
    Write-Host "WARNING: Elements are expired. Check CelesTrak access." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "ERROR: Pre-fetch failed. Run the app anyway — it will use cached or sample data." -ForegroundColor Red
}
