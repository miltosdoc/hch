@echo off
REM ============================================================
REM Webdoc Batch Upload - Remiss Documents
REM ============================================================
REM This script uploads files to Webdoc based on personnummer
REM extracted from the filename.
REM
REM Usage:
REM   upload_remiss.bat              - Process files in 'images' folder
REM   upload_remiss.bat C:\path\to   - Process files in specified folder
REM
REM Filename format: Include personnummer in the filename
REM Examples:
REM   19121212-1212.jpg
REM   remiss_19121212-1212.pdf
REM   patient_191212121212_scan.jpg
REM ============================================================

echo.
echo ============================================================
echo    Webdoc Batch Upload - Remiss Documents
echo ============================================================
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Run the batch upload script
if "%~1"=="" (
    echo Processing files in default 'images' folder...
    python batch_upload.py
) else (
    echo Processing files in: %~1
    python batch_upload.py "%~1"
)

echo.
if errorlevel 1 (
    echo ============================================================
    echo    Some uploads failed. Check the output above for details.
    echo ============================================================
) else (
    echo ============================================================
    echo    All uploads completed successfully!
    echo ============================================================
)

echo.
pause
