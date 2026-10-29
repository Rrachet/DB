@echo off
cd /d "%~dp0"
title DB (voice)
call .venv\Scripts\activate.bat
python -m db --voice
