@echo off
cd /d "%~dp0"

echo ===================================================
echo     Starting MarketPulse AI Trading Ecosystem
echo ===================================================
echo.

:: ── Preflight: Locate Python Virtual Environment (env or venv) ──
set "PY_EXEC="
set "UVI_EXEC="

if exist "%~dp0env\Scripts\python.exe" (
    set "PY_EXEC=%~dp0env\Scripts\python.exe"
    set "UVI_EXEC=%~dp0env\Scripts\uvicorn.exe"
) else if exist "env\Scripts\python.exe" (
    set "PY_EXEC=env\Scripts\python.exe"
    set "UVI_EXEC=env\Scripts\uvicorn.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_EXEC=%~dp0venv\Scripts\python.exe"
    set "UVI_EXEC=%~dp0venv\Scripts\uvicorn.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PY_EXEC=venv\Scripts\python.exe"
    set "UVI_EXEC=venv\Scripts\uvicorn.exe"
)

if not defined PY_EXEC (
    echo [ERROR] Virtual environment not found at env\Scripts\python.exe
    echo         Run: python -m venv env
    echo         Then: env\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: ── Preflight: Check PostgreSQL is running ──
echo [1/3] Checking PostgreSQL...
powershell -Command "try { $c = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 5432); $c.Close(); Write-Host '      PostgreSQL is running.' } catch { Write-Host '      PostgreSQL is NOT running. Attempting to start...'; Start-Process powershell -Verb runAs -ArgumentList '-Command Start-Service postgresql-x64-18' -Wait; Start-Sleep -Seconds 3 }"

:: ── Set environment for imports ──
set PYTHONPATH=%~dp0marketpulse;%~dp0web_scraper
echo       Connected 7-Stage Modular Stock Scraper.

:: ── Launch Backend ──
echo [2/3] Starting Backend FastAPI Server...
start "MarketPulse Backend API" cmd /k "cd /d "%~dp0marketpulse" && "%UVI_EXEC%" app.api.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo [3/3] Backend launched!
echo.
echo ===================================================
echo   MarketPulse is ready at:  http://127.0.0.1:8000
echo   API Docs at:              http://127.0.0.1:8000/docs
echo ===================================================
echo.
pause
