# Odysseus stoppen - Container beenden, GPU/RAM freigeben.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$dockerBin = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (Test-Path $dockerBin) {
    $env:Path = "$(Split-Path $dockerBin);$env:Path"
    Write-Host "Stoppe Odysseus-Container..." -ForegroundColor Yellow
    docker compose down
}

$ollama = Get-Process ollama -ErrorAction SilentlyContinue
if ($ollama) {
    Write-Host "Stoppe Ollama (GPU-Speicher frei)..." -ForegroundColor Yellow
    Stop-Process -Name ollama -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Odysseus gestoppt. Docker Desktop kann im Tray beendet werden (Rechtsklick -> Quit)." -ForegroundColor Green
Write-Host "Beim naechsten Mal: Odysseus starten.lnk oder start-odysseus.ps1" -ForegroundColor DarkGray
