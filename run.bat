@echo off
echo ============================================
echo    JARVIS v4 - Starting...
echo ============================================
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run JARVIS
python jarvis_main.py

echo.
echo JARVIS has shut down.
pause
