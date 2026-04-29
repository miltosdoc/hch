@echo off
:: ============================================================
:: HCH Services - Master Auto-Start Script
:: Starts ALL services on login:
::   1. Docker (Pulsus Holter Tracker)
::   2. Integrationsportalen (Flask, port 5000)
::   3. EKG Arkiv (PowerShell, port 8085)
::   4. Holter Review (Flask, port 8086)
:: ============================================================

title HCH Services - Starting...

:: Wait for Docker Desktop to be ready (max 120 seconds)
echo [1/4] Waiting for Docker Desktop...
set /a count=0
:wait_docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    set /a count+=5
    if %count% geq 120 (
        echo ERROR: Docker Desktop did not start within 120 seconds.
        echo Please start Docker Desktop manually, then run this script again.
        pause
        exit /b 1
    )
    timeout /t 5 /nobreak >nul
    goto wait_docker
)

echo Docker is ready.

:: ─────────────────────────────────────────────────────────
:: 1. Start Pulsus Holter Tracker (Docker Compose)
:: ─────────────────────────────────────────────────────────
echo [1/4] Starting Pulsus Holter Tracker (Docker)...
cd /d "c:\Users\Miltiadis.t\Desktop\WebdocAPI\Holter Flow"
docker compose up -d
echo       Pulsus running at http://localhost:8080

:: ─────────────────────────────────────────────────────────
:: 2. Start Integrationsportalen (Flask app, port 5000)
:: ─────────────────────────────────────────────────────────
echo [2/4] Starting Integrationsportalen...
cd /d "c:\Users\Miltiadis.t\Desktop\WebdocAPI"
:: Check if already running by testing port 5000
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5000' -TimeoutSec 2 -UseBasicParsing; Write-Output 'Already running.' } catch { cscript //nologo run_background.vbs; Write-Output 'Started.' }"
echo       Integrationsportalen at http://localhost:5000

:: ─────────────────────────────────────────────────────────
:: 3. Start EKG Arkiv (PowerShell HTTP server, port 8085)
:: ─────────────────────────────────────────────────────────
echo [3/4] Starting EKG Arkiv...
cd /d "c:\Users\Miltiadis.t\Desktop\WebdocAPI\ECG-Viewer"
:: Check if already running by testing port 8085
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8085' -TimeoutSec 2 -UseBasicParsing; Write-Output 'Already running.' } catch { cscript //nologo run_ecg_viewer.vbs; Write-Output 'Started.' }"
echo       EKG Arkiv at http://localhost:8085

:: ─────────────────────────────────────────────────────────
:: 4. Start Holter Review (Flask, port 8086)
:: ─────────────────────────────────────────────────────────
echo [4/4] Starting Holter Review...
cd /d "c:\Users\Miltiadis.t\Desktop\WebdocAPI\Holter Review"
:: Check if already running by testing port 8086
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8086' -TimeoutSec 2 -UseBasicParsing; Write-Output 'Already running.' } catch { cscript //nologo run_holter_review.vbs; Write-Output 'Started.' }"
echo       Holter Review at http://localhost:8086

echo.
echo ============================================================
echo   ALL SERVICES STARTED:
echo   - Pulsus Holter Tracker  : http://localhost:8080
echo   - Integrationsportalen   : http://localhost:5000
echo   - EKG Arkiv              : http://localhost:8085
echo   - Holter Review          : http://localhost:8086
echo ============================================================
echo.
echo This window will close in 10 seconds...
timeout /t 10 /nobreak >nul

