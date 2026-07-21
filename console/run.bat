@echo off
setlocal enabledelayedexpansion

set "CONSOLE_DIR=%~dp0"
set "CONSOLE_ROOT=%CONSOLE_DIR:~0,-1%"
set "VENV_DIR=%CONSOLE_DIR%.venv"
set "PID_FILE=%CONSOLE_DIR%.console.pid"
set "MARKER=%VENV_DIR%\.installed"
set "REQUIREMENTS=%CONSOLE_DIR%requirements.txt"

:: --- Kill any running console instance ---
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    if defined OLD_PID (
        echo Stopping existing console (PID !OLD_PID!)...
        taskkill /PID !OLD_PID! /F >nul 2>&1
    )
    del "%PID_FILE%"
)

:: --- Create venv if it doesn't exist ---
if not exist "%VENV_DIR%\" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 ( echo Failed to create virtual environment. & exit /b 1 )
)

:: --- Install/update dependencies if needed ---
set "NEEDS_INSTALL=1"
if exist "%MARKER%" (
    for /f %%R in ('powershell -NoProfile -Command "if ((Get-Item '%REQUIREMENTS%').LastWriteTime -gt (Get-Item '%MARKER%').LastWriteTime) { 'yes' } else { 'no' }"') do set "NEWER=%%R"
    if /i "!NEWER!"=="no" set "NEEDS_INSTALL=0"
)
if "!NEEDS_INSTALL!"=="1" (
    echo Installing dependencies...
    "%VENV_DIR%\Scripts\pip.exe" install --quiet --upgrade pip
    "%VENV_DIR%\Scripts\pip.exe" install --quiet -r "%REQUIREMENTS%"
    if errorlevel 1 ( echo Dependency installation failed. & exit /b 1 )
    type nul > "%MARKER%"
)

:: --- Start console ---
if not defined PORT set "PORT=8080"
if not defined HOST set "HOST=0.0.0.0"
if not defined MCP_URL set "MCP_URL=http://localhost:9030/mcp"

echo Starting console (port: %PORT%, MCP_URL: %MCP_URL%)...
set "MCP_URL=%MCP_URL%"
powershell -NoProfile -Command "$p = Start-Process -FilePath '%VENV_DIR%\Scripts\uvicorn.exe' -ArgumentList 'app:app','--host','%HOST%','--port','%PORT%','--app-dir','%CONSOLE_ROOT%' -NoNewWindow -PassThru; $p.Id | Out-File -FilePath '%PID_FILE%' -Encoding ascii -NoNewline"

set /p CONSOLE_PID=<"%PID_FILE%"
echo Console started (PID %CONSOLE_PID%). PID saved to %PID_FILE%
endlocal
