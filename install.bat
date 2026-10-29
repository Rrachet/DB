@echo off
REM One-time setup for DB. Double-click this file.
cd /d "%~dp0"
where python >nul 2>nul || (echo Python not found. Install it from https://www.python.org/downloads/ and tick "Add to PATH". & pause & exit /b 1)
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-desktop.txt
echo.
echo Done. If you haven't yet, set a free Gemini key from https://aistudio.google.com/apikey
echo (then open a new window):
echo   setx GEMINI_API_KEY "your-key"
echo Start DB with start_db.bat (typing) or start_db_voice.bat (hands-free).
pause
