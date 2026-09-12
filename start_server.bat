@echo off
title SmartQueue Server
echo =======================================================
echo   SmartQueue: Intelligent Queue Management System
echo =======================================================
echo.
echo Starting Flask Server on http://127.0.0.1:5000 ...
echo.
cd /d "%~dp0"
.venv\Scripts\python.exe app.py
pause
