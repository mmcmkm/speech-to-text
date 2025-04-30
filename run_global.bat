@echo off
chcp 65001
setlocal EnableDelayedExpansion

set "APP_ROOT=%~dp0"
cd /d "%APP_ROOT%"

if not exist "logs" mkdir logs

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

if "%GEMINI_API_KEY%"=="" (
    echo GEMINI_API_KEY environment variable is not set
    pause
    exit /b 1
)

pythonw "%APP_ROOT%main.py"
if %errorlevel% neq 0 (
    echo Application failed to start
    pause
    exit /b 1
)

exit /b 0 