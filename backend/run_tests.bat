@echo off
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" -m pytest tests/ -v 2>&1
) else (
    python -m pytest tests/ -v 2>&1
)
pause
