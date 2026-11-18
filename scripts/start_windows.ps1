# Start FinAlly (idempotent). Usage: .\start_windows.ps1 [-Build] [-Open]
param([switch]$Build, [switch]$Open)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path .env)) {
    if (Test-Path .env.example) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example (edit it to set OPENROUTER_API_KEY)." }
    else { New-Item .env -ItemType File | Out-Null }
}

docker image inspect finally *> $null
$missing = ($LASTEXITCODE -ne 0)
if ($Build -or $missing) {
    Write-Host "Building image..."
    docker build -t finally .
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

docker rm -f finally *> $null
docker run -d --name finally -v finally-data:/app/db -p 8000:8000 --env-file .env finally | Out-Null
if ($LASTEXITCODE -ne 0) { exit 1 }

$url = "http://localhost:8000"
Write-Host "FinAlly is running at $url"
if ($Open) { Start-Process $url }
