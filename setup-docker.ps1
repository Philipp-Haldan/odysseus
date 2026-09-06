#Requires -RunAsAdministrator
<#
  Odysseus Docker Setup fuer Windows 11 (einmalig, als Administrator).

  Rechtsklick -> "Mit PowerShell ausfuehren" ODER in Admin-PowerShell:
    cd <path-to-your-odysseus-clone>
    powershell -ExecutionPolicy Bypass -File .\setup-docker.ps1
#>
$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Odysseus Docker Setup (Windows 11)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# --- Schritt 1: WSL2 ---
Write-Host "[1/5] WSL2 installieren..." -ForegroundColor Yellow
wsl --install --no-distribution
$wslExit = $LASTEXITCODE
if ($wslExit -eq 0) {
    Write-Host "      WSL2 wurde installiert oder war bereits aktiv." -ForegroundColor Green
} else {
    Write-Host "      WSL-Befehl beendet mit Code $wslExit (evtl. schon installiert)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/5] WICHTIG: PC jetzt NEU STARTEN" -ForegroundColor Red
Write-Host "      Nach dem Neustart:" -ForegroundColor White
Write-Host "        1. Docker Desktop aus dem Startmenue starten" -ForegroundColor White
Write-Host "        2. Warten bis unten links 'Engine running' steht" -ForegroundColor White
Write-Host "        3. Dieses Skript nochmal ausfuehren ODER start-docker-odysseus.ps1" -ForegroundColor White
Write-Host ""

$reboot = Read-Host "Jetzt neu starten? (j/n)"
if ($reboot -match '^[jJyY]') {
    Restart-Computer -Force
    exit 0
}

# --- Schritt 3: Docker pruefen ---
Write-Host "[3/5] Docker Desktop pruefen..." -ForegroundColor Yellow
$dockerBin = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (-not (Test-Path $dockerBin)) {
    Write-Host "      Docker Desktop fehlt. Installiere mit:" -ForegroundColor Red
    Write-Host "      winget install Docker.DockerDesktop" -ForegroundColor White
    Read-Host "Enter druecken zum Beenden"
    exit 1
}

$desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Write-Host "      Starte Docker Desktop..." -ForegroundColor Yellow
    Start-Process $desktop
}

$env:Path = "$(Split-Path $dockerBin);$env:Path"
Write-Host "[4/5] Warte auf Docker Engine (max. 5 Min.)..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 60; $i++) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; Write-Host "      Docker laeuft." -ForegroundColor Green; break }
    Write-Host "      ... noch nicht bereit ($i/60)" -ForegroundColor DarkGray
    Start-Sleep -Seconds 5
}
if (-not $ready) {
    Write-Host "      Docker ist noch nicht bereit. Starte Docker Desktop manuell und fuehre danach aus:" -ForegroundColor Red
    Write-Host "      powershell -ExecutionPolicy Bypass -File .\start-docker-odysseus.ps1" -ForegroundColor White
    Read-Host "Enter druecken zum Beenden"
    exit 1
}

# --- Schritt 5: Odysseus starten ---
Write-Host "[5/5] Odysseus per Docker Compose starten..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

$conn = Get-NetTCPConnection -LocalPort 7000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "      Port 7000 ist belegt (evtl. native Odysseus). Beende den Prozess..." -ForegroundColor Yellow
    foreach ($pid in ($conn.OwningProcess | Select-Object -Unique)) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "      docker compose fehlgeschlagen. Siehe Ausgabe oben." -ForegroundColor Red
    Read-Host "Enter druecken zum Beenden"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Fertig!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Browser:  http://localhost:7000" -ForegroundColor White
Write-Host "  Passwort: docker compose logs odysseus" -ForegroundColor White
Write-Host "            (Zeile mit 'Temporary password')" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Ollama auf Windows laeuft weiter ueber:" -ForegroundColor White
Write-Host "  http://host.docker.internal:11434/v1 (in .env gesetzt)" -ForegroundColor DarkGray
Write-Host ""
Read-Host "Enter druecken zum Beenden"
