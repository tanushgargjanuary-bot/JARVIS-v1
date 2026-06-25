@echo off
echo ==========================================
echo     JARVIS v3 - Windows Installer
echo ==========================================
echo.

REM Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python detected.
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [WARNING] Could not create venv. Installing globally...
    ) else (
        echo [OK] Virtual environment created.
    )
) else (
    echo [OK] Virtual environment already exists.
)

REM Activate virtual environment
call venv\Scripts\activate.bat 2>nul

echo.
echo [INFO] Installing Python packages...
echo This may take a few minutes...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install packages.
    echo Try running: pip install -r requirements.txt manually
    pause
    exit /b 1
)

echo [OK] All packages installed.
echo.

REM Create required folders
echo [INFO] Creating project folders...
if not exist memory mkdir memory
if not exist notes mkdir notes
if not exist screenshots mkdir screenshots
if not exist logs mkdir logs
echo [OK] Folders created.

REM Copy .env.example to .env if .env doesn't exist
if not exist .env (
    echo [INFO] Creating .env file from template...
    copy .env.example .env >nul
    echo [OK] .env created. Please edit it and add your Groq API key.
    echo.
    echo ==========================================
    echo     NEXT STEPS:
    echo ==========================================
    echo 1. Edit .env file: notepad .env
    echo 2. Add your Groq API key from https://console.groq.com/keys
    echo 3. Set your name and city
    echo 4. Run: run.bat
    echo ==========================================
) else (
    echo [OK] .env file already exists.
)

echo.
echo ==========================================
echo     Installation Complete!
echo ==========================================
echo.
pause
