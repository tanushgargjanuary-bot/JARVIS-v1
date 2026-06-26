@echo off
echo ============================================
echo    JARVIS v4 - Installation
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.9+ from python.org
    pause
    exit /b 1
)

echo [1/5] Python found.
echo.

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo [2/5] Creating virtual environment...
    python -m venv venv
) else (
    echo [2/5] Virtual environment exists.
)

echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [4/5] Installing dependencies (this may take a few minutes)...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [5/5] Creating directories...
if not exist memory mkdir memory
if not exist notes mkdir notes
if not exist screenshots mkdir screenshots
if not exist logs mkdir logs
if not exist rag mkdir rag
if not exist rag\documents mkdir rag\documents
if not exist rag\chroma_db mkdir rag\chroma_db

echo.
echo ============================================
echo    Installation Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env and add your Groq API key
echo 2. Run: run.bat
echo.
pause
