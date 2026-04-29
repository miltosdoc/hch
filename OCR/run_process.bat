@echo off
echo ========================================================
echo Setting up and running Personnummer Renamer
echo ========================================================

echo.
echo [1/2] Checking and installing Python dependencies...
pip install Pillow pytesseract

echo.
echo [2/2] Starting process_files.py...
echo.

REM Create a temporary drive mapping for the script directory (handles UNC paths)
pushd "%~dp0"

python process_files.py

REM Remove the temporary drive mapping
popd

echo.
echo ========================================================
echo Execution finished. Check above for any errors.
echo Press any key to accept and close this window.
pause
