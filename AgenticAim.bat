@echo off
title AgenticAim — AI-Powered Esports Aim Coach
color 0b

echo ======================================================================
echo           AGENTICAIM — ESPORTS AIM COACH & HARDWARE ADVISOR           
echo                       AMD Developer Hackathon III                     
echo ======================================================================
echo.
echo [*] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.11+ and try again.
    pause
    exit /b
)

echo [*] Launching Native Desktop App...
python desktop_app.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Desktop app exited.
    pause
)
