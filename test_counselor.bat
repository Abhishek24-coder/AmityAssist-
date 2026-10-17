@echo off
title UniAssist AI Counselor - Interactive Test Console
cd /d "%~dp0"

echo ========================================================
echo       UniAssist AI Counselor (Chat + Voice) Tester
echo ========================================================
echo.

if exist .venv\Scripts\python.exe (
    set PYTHON_EXE=.venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

%PYTHON_EXE% test_counselor.py
pause
