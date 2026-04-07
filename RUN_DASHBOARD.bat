@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [STEP 1] Environment Check...
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment missing or broken. Re-creating...
    python -m venv .venv
)

echo [STEP 2] Syncing Dependencies (Please wait)...
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [CRITICAL ERROR] Failed to install dependencies. 
    echo Please check your internet connection or Python installation.
    pause
    exit /b
)

echo [STEP 3] Launching ICT Dashboard...
echo [INFO] Local URL should be http://localhost:8501
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address localhost

if %errorlevel% neq 0 (
    echo [ERROR] Streamlit failed to start. 
    echo Try running: .\.venv\Scripts\python.exe -m pip install streamlit
    pause
)
pause
