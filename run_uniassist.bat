@echo off
setlocal
cd /d "%~dp0"
title UniAssist Enterprise Launcher
echo ===================================================
echo     Starting UniAssist Enterprise Platform...
echo ===================================================
UniAssist.exe %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Fallback Launcher] Launching directly...
    start /b "" ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
    timeout /t 2 /nobreak >nul
    start "" "msedge.exe" --app="http://127.0.0.1:8000/" --no-proxy-server
)
