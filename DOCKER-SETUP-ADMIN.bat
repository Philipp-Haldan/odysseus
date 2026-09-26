@echo off
title Odysseus Docker Setup (Administrator)
echo Starte Docker-Setup mit Administrator-Rechten...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0setup-docker.ps1""'"
