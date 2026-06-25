@echo off
echo ==========================================
echo     JARVIS v3 - Text Mode Launcher
echo ==========================================
echo.

REM Check Python
call python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+.
    pause
    exit /b 1
)

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated.
) else (
    echo [INFO] No virtual environment found. Using global Python.
)

REM Check .env exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo Creating from template. Please edit it and add your Groq API key.
    copy .env.example .env >nul 2>&1
)

echo.
echo [INFO] Starting JARVIS v3 in Text Mode...
echo [INFO] No microphone required. Type commands at the prompt.
echo.

REM Set environment variable to skip mic test
set JARVIS_TEXT_MODE=1

REM Launch JARVIS - mic will fail and auto-switch to text mode
python jarvis_main.py

echo.
echo JARVIS has exited.
if errorlevel 1 pause
