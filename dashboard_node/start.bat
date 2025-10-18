@echo off
title Smart Kitchen Dashboard
cd /d %~dp0

echo.
echo  =========================================
echo   Smart Kitchen Hygiene Monitor
echo   Node.js Dashboard Server
echo  =========================================
echo.

:: Check if Node.js is installed
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Node.js not found!
    echo  Please install from: https://nodejs.org
    pause
    exit /b 1
)

:: Install dependencies if node_modules missing
if not exist "node_modules\" (
    echo  [SETUP] Installing dependencies...
    npm install
    echo  [SETUP] Done!
    echo.
)

echo  [INFO] Starting server...
echo  [INFO] Open browser at: http://127.0.0.1:3000
echo  [INFO] Press Ctrl+C to stop
echo.

node server.js
pause
