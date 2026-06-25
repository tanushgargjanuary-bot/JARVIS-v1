@echo off
echo ============================================
echo    JARVIS v4 - Text Mode
echo ============================================
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run JARVIS in text-only mode
python -c "import jarvis_main; jarvis_main.text_mode()"

echo.
echo JARVIS has shut down.
pause
