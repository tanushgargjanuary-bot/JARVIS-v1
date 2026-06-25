@echo off
echo ==========================================
echo     JARVIS v3 - Voice Mode Launcher
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
    notepad .env
)

REM Check .env has real API key
findstr /C:"your_groq_key_here" .env >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] GROQ_API_KEY not set in .env file!
    echo Get your free key at: https://console.groq.com/keys
    echo.
    choice /C YN /M "Do you want to edit .env now"
    if errorlevel 2 exit /b 1
    if errorlevel 1 notepad .env
)

REM Launch JARVIS
echo.
echo [INFO] Starting JARVIS v3 in Voice Mode...
echo.
python jarvis_main.py

REM Handle exit
echo.
echo JARVIS has exited.

REM Check for errors
if errorlevel 1 (
    echo.
    echo [ERROR] JARVIS exited with an error.
    echo Check the error message above.
    echo.
    echo Common fixes:
    echo - Run: install.bat
    echo - Check your .env file has a valid GROQ_API_KEY
    echo - Make sure microphone is connected
    echo.
    pause
)
