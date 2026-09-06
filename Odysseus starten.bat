@echo off
title Odysseus starten
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-odysseus.ps1"
if errorlevel 1 pause
