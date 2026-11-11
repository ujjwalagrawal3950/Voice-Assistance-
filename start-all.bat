@echo off
REM Virtual KAM - Start All Services
echo ==========================================
echo  Virtual KAM - Starting All Services
echo ==========================================

cd /d "%~dp0"

REM 0. Ollama (temporarily commented out while using Google Gemini API)
REM netstat -ano | findstr ":11434 " | findstr "LISTENING" >nul
REM if errorlevel 1 (
REM     echo [0/3] Starting Ollama (http://127.0.0.1:11434)...
REM     start "Virtual KAM - Ollama" cmd /k "ollama serve"
REM     timeout /t 2 /nobreak >nul
REM )

REM 1. Backend (Python 3.15, FastAPI)
echo [1/3] Starting Backend (http://127.0.0.1:8000)...
start "Virtual KAM - Backend" cmd /k ".\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --app-dir backend --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

REM 2. Voice Service (Python 3.13, Whisper STT + Piper TTS)
echo [2/3] Starting Voice Service (ws://localhost:8765)...
start "Virtual KAM - Voice Service" cmd /k ".\.venv-voice\Scripts\python.exe voice-service\main.py"

timeout /t 2 /nobreak >nul

REM 3. Frontend (Vite + React)
echo [3/3] Starting Frontend (http://localhost:5173)...
start "Virtual KAM - Frontend" /D "%~dp0frontend" cmd /k "npm run dev -- --port 5173"

echo.
echo ==========================================
echo  All services launched in separate windows!
echo ==========================================
echo  Backend:       http://127.0.0.1:8000
echo  API Docs:      http://127.0.0.1:8000/docs
echo  Voice Service: ws://localhost:8765
echo  Frontend:      http://localhost:5173
echo ==========================================
echo  Note: Using Google Gemini API for LLM + Local Whisper STT / Piper TTS
echo.
pause
