@echo off
title Odysseus ZeroTier Firewall (Administrator)
echo Erstellt Firewall-Regel fuer Odysseus Remote-Zugriff (ZeroTier, Port 7000)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$n='Odysseus ZeroTier'; if (Get-NetFirewallRule -DisplayName $n -ErrorAction SilentlyContinue) { Write-Host 'Regel existiert bereits.' -ForegroundColor Green } else { New-NetFirewallRule -DisplayName $n -Direction Inbound -Protocol TCP -LocalPort 7000 -RemoteAddress 10.31.0.0/16 -Action Allow; Write-Host 'Fertig.' -ForegroundColor Green }"
echo.
pause
