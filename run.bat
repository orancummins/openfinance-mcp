@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR:~0,-1%"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "PID_FILE=%SCRIPT_DIR%.server.pid"
set "MARKER=%VENV_DIR%\.installed"
set "PYPROJECT=%SCRIPT_DIR%pyproject.toml"

:: --- Kill any running server instance ---
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    if defined OLD_PID (
        echo Stopping existing server ^(PID !OLD_PID!^)...
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
    for /f %%R in ('powershell -NoProfile -Command "if ((Get-Item '%PYPROJECT%').LastWriteTime -gt (Get-Item '%MARKER%').LastWriteTime) { 'yes' } else { 'no' }"') do set "NEWER=%%R"
    if /i "!NEWER!"=="no" set "NEEDS_INSTALL=0"
)
if "!NEEDS_INSTALL!"=="1" (
    echo Installing dependencies...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --quiet --upgrade pip
    "%VENV_DIR%\Scripts\python.exe" -m pip install --quiet -e "%REPO_ROOT%[console]"
    if errorlevel 1 ( echo Dependency installation failed. & exit /b 1 )
    type nul > "%MARKER%"
)

:: --- Start server ---
if not defined TRANSPORT set "TRANSPORT=http"
if not defined HOST set "HOST=0.0.0.0"
if not defined PORT set "PORT=9030"

echo Starting openfinance-mcp server (transport: %TRANSPORT%, port: %PORT%)...
powershell -NoProfile -Command "$p = Start-Process -FilePath '%VENV_DIR%\Scripts\openfinance-mcp.exe' -ArgumentList '--transport','%TRANSPORT%','--host','%HOST%','--port','%PORT%' -NoNewWindow -PassThru; $p.Id | Out-File -FilePath '%PID_FILE%' -Encoding ascii -NoNewline"

set /p SERVER_PID=<"%PID_FILE%"
echo Server started (PID %SERVER_PID%). PID saved to %PID_FILE%
endlocal
