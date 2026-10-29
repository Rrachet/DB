@echo off
REM One-time setup for DB. Double-click this file.
cd /d "%~dp0"
where python >nul 2>nul || (echo Python not found. Install it from https://www.python.org/downloads/ and tick "Add to PATH". & pause & exit /b 1)
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Done. If you haven't yet, set your API key (then open a new window):
echo   setx ANTHROPIC_API_KEY "sk-ant-..."
echo Start DB with start_db.bat (typing) or start_db_voice.bat (hands-free).
pause
