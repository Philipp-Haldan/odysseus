# Odysseus starten (Docker + Ollama) und Oberflaeche im Browser oeffnen.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$OdysseusUrl = "http://localhost:7000"
$dockerBin = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$ollamaDir = "$env:LOCALAPPDATA\Programs\Ollama"

function Test-OdysseusWeb {
    param([string]$Url)
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -MaximumRedirection 5
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Wait-ForOdysseusWeb {
    param([string]$Url, [int]$MaxSeconds = 180)
    Write-Host "Warte bis Odysseus-Oberflaeche bereit ist..." -ForegroundColor Yellow
    for ($i = 1; $i -le $MaxSeconds; $i++) {
        if (Test-OdysseusWeb -Url $Url) {
            Write-Host "Odysseus ist bereit." -ForegroundColor Green
            return $true
        }
        if ($i % 10 -eq 0) {
            Write-Host "  ... noch warten ($i s)" -ForegroundColor DarkGray
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Open-OdysseusBrowser {
    param([string]$Url)
    Write-Host "Oeffne Odysseus im Browser: $Url" -ForegroundColor Green
    Start-Process $Url
}

function Test-DockerEngine {
    param([string]$DockerExe)
    $job = Start-Job -ScriptBlock {
        param($Exe)
        & $Exe ps -q 2>$null | Out-Null
        return $LASTEXITCODE
    } -ArgumentList $DockerExe
    $done = Wait-Job $job -Timeout 8
    if (-not $done) {
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
        return $false
    }
    $code = Receive-Job $job
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    return ($code -eq 0)
}

function Wait-ForDockerEngine {
    param([string]$DockerExe, [string]$DesktopExe, [int]$MaxSeconds = 300)
    Write-Host "Warte auf Docker Engine (max. $([int]($MaxSeconds/60)) Min.)..." -ForegroundColor Yellow
    for ($i = 1; $i -le $MaxSeconds; $i++) {
        if (Test-DockerEngine -DockerExe $DockerExe) {
            Write-Host "Docker Engine laeuft." -ForegroundColor Green
            return $true
        }
        if ($i -eq 1 -or ($i % 10 -eq 0)) {
            if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
                Write-Host "  Starte Docker Desktop..." -ForegroundColor Cyan
                Start-Process $DesktopExe
            } else {
                Write-Host "  ... Docker startet noch ($i s)" -ForegroundColor DarkGray
            }
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Stop-NativeOdysseusOnPort7000 {
    $conn = Get-NetTCPConnection -LocalPort 7000 -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) { return }
    foreach ($procId in ($conn.OwningProcess | Select-Object -Unique)) {
        if ($procId -eq $PID) { continue }
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc) { continue }
        $name = $proc.ProcessName.ToLowerInvariant()
        # Nur native Python/Uvicorn beenden - niemals Docker-Prozesse auf Port 7000
        if ($name -in @("python", "python3", "uvicorn")) {
            Write-Host "Beende alte native Odysseus-Instanz (PID $procId)..." -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

# --- Bereits erreichbar? Nur Browser oeffnen ---
if (Test-OdysseusWeb -Url $OdysseusUrl) {
    Write-Host "Odysseus laeuft bereits." -ForegroundColor Green
    Open-OdysseusBrowser -Url $OdysseusUrl
    exit 0
}

if (-not (Test-Path $dockerBin)) {
    Write-Host "Docker Desktop fehlt." -ForegroundColor Red
    exit 1
}
$env:Path = "$(Split-Path $dockerBin);$env:Path"

if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Write-Host "Starte Docker Desktop..." -ForegroundColor Cyan
    Start-Process $dockerDesktop
}

if (-not (Wait-ForDockerEngine -DockerExe $dockerBin -DesktopExe $dockerDesktop)) {
    Write-Host ""
    Write-Host "Docker Engine ist nicht bereit." -ForegroundColor Red
    Write-Host "Bitte Docker Desktop manuell starten und warten bis 'Engine running'." -ForegroundColor Yellow
    Write-Host "Dann erneut 'Odysseus starten' klicken." -ForegroundColor Yellow
    exit 1
}

$env:OLLAMA_KEEP_ALIVE = "5m"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
if (Test-Path $ollamaDir) { $env:Path = "$ollamaDir;$env:Path" }
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Starte Ollama..." -ForegroundColor Cyan
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Stop-NativeOdysseusOnPort7000

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host "Starte Odysseus-Container..." -ForegroundColor Cyan
$composeOk = $false
$prevEa = $ErrorActionPreference
$ErrorActionPreference = "Continue"
for ($attempt = 1; $attempt -le 3; $attempt++) {
    docker compose up -d 2>&1 | Write-Host
    if ($LASTEXITCODE -eq 0) {
        $composeOk = $true
        break
    }
    if ($attempt -lt 3) {
        Write-Host "docker compose fehlgeschlagen - erneuter Versuch ($attempt/3)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        Wait-ForDockerEngine -DockerExe $dockerBin -DesktopExe $dockerDesktop -MaxSeconds 60 | Out-Null
    }
}
$ErrorActionPreference = $prevEa
if (-not $composeOk) {
    Write-Host "Container konnten nicht gestartet werden. Ist Docker Desktop wirklich 'Engine running'?" -ForegroundColor Red
    exit 1
}

if (Wait-ForOdysseusWeb -Url $OdysseusUrl) {
    Open-OdysseusBrowser -Url $OdysseusUrl
} else {
    Write-Host "Odysseus antwortet noch nicht - Browser trotzdem oeffnen..." -ForegroundColor Yellow
    Open-OdysseusBrowser -Url $OdysseusUrl
}
